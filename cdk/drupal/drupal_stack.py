import os
import subprocess

from aws_cdk import (
    Aws,
    aws_iam,
    aws_sns,
    CfnCondition,
    CfnOutput,
    CfnParameter,
    Fn,
    Stack
)
from constructs import Construct

from oe_patterns_cdk_common.alb import Alb
from oe_patterns_cdk_common.asg import Asg
from oe_patterns_cdk_common.aurora_cluster import AuroraMysql
from oe_patterns_cdk_common.db_secret import DbSecret
from oe_patterns_cdk_common.dns import Dns
from oe_patterns_cdk_common.efs import Efs
from oe_patterns_cdk_common.elasticache_cluster import ElasticacheMemcached
from oe_patterns_cdk_common.util import Util
from oe_patterns_cdk_common.vpc import Vpc

if 'TEMPLATE_VERSION' in os.environ:
    template_version = os.environ['TEMPLATE_VERSION']
else:
    try:
        template_version = subprocess.check_output(["git", "describe"]).strip().decode('ascii')
    except Exception:
        template_version = "CICD"

# Updated each release in Phase 3 (dev AMI) and Phase 6 prereqs (prod AMI).
AMI_ID = "ami-03f6af23dfb830a96"  # ordinary-experts-patterns-drupal-3.1.0-20260720-0852 (dev AMI for testing)
NEXT_RELEASE_PREFIX = "v310"


class DrupalStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        #
        # PARAMETERS
        #

        notification_email_param = CfnParameter(
            self,
            "NotificationEmail",
            default="",
            description="Optional: Email address that receives operational notifications. Used only by this stack to subscribe to an SNS topic; not sent to any third party."
        )

        #
        # CONDITIONS
        #

        notification_email_exists_condition = CfnCondition(
            self,
            "NotificationEmailExists",
            expression=Fn.condition_not(Fn.condition_equals(notification_email_param.value, ""))
        )

        #
        # COMMON-LIBRARY CONSTRUCTS
        #

        vpc = Vpc(self, "Vpc")
        dns = Dns(self, "Dns")

        db_secret = DbSecret(self, "DbSecret")
        db = AuroraMysql(self, "Db", db_secret=db_secret, vpc=vpc, database_name="drupal")

        # Memcached: always provisioned. Default 2 nodes because cdk-common's
        # ElasticacheMemcached hard-codes az_mode="cross-az" which AWS rejects
        # with num_cache_nodes=1.
        memcached = ElasticacheMemcached(self, "ElastiCache", vpc=vpc)
        memcached.elasticache_cluster_num_cache_nodes_param.default = 2

        # notifications
        notification_topic = aws_sns.CfnTopic(
            self,
            "NotificationTopic",
            topic_name=Fn.join("-", [Aws.STACK_NAME, "notifications", Fn.select(2, Fn.split("/", Aws.STACK_ID))])
        )
        notification_subscription = aws_sns.CfnSubscription(
            self,
            "NotificationSubscription",
            protocol="email",
            topic_arn=notification_topic.ref,
            endpoint=notification_email_param.value_as_string
        )
        notification_subscription.cfn_options.condition = notification_email_exists_condition

        # ASG
        with open("drupal/app_launch_config_user_data.sh") as f:
            app_launch_config_user_data = f.read()
        asg = Asg(
            self,
            "Asg",
            ami_id=AMI_ID,
            ami_id_param_name_suffix=NEXT_RELEASE_PREFIX,
            # Default is 15 min; first-boot user_data copies ~26.5k files
            # (the composer-installed Drupal codebase) from the AMI to EFS,
            # which alone takes ~12-13 min over NFS, leaving too little
            # margin for the rest of user_data (secrets fetch, cert gen,
            # apache start, cfn-signal) to finish before the ASG times out.
            create_and_update_timeout_minutes=25,
            secret_arns=[db_secret.secret_arn()],
            use_graviton=False,
            user_data_contents=app_launch_config_user_data,
            user_data_variables={
                "DbSecretArn": db_secret.secret_arn(),
                "DrupalSalt": Fn.base64(Aws.STACK_ID),
                "Hostname": dns.hostname(),
            },
            vpc=vpc
        )

        # ALB + DNS wiring
        #
        # health_check_path is /robots.txt, not /: ALB health checks send the
        # target's own IP as the Host header, which Drupal's trusted_host_patterns
        # rejects with a 400. /robots.txt is a static file Apache serves directly,
        # bypassing Drupal's bootstrap (and the host check) entirely.
        alb = Alb(self, "Alb", asg=asg, vpc=vpc, health_check_path="/robots.txt")
        asg.asg.target_group_arns = [alb.target_group.ref]
        dns.add_alb(alb)

        # EFS for /sites/default/files (shared) AND the entire Drupal codebase
        # (the AMI bakes /root/drupal which user_data copies into EFS on first
        # boot, then Apache symlinks /var/www/app/drupal -> /mnt/efs/drupal).
        efs = Efs(self, "Efs", app_sg=asg.sg, vpc=vpc)

        # security group ingress
        Util.add_sg_ingress(db, asg.sg)
        Util.add_sg_ingress(memcached, asg.sg)

        # cross-resource dependencies — ASG must wait for the DB cluster to
        # come up so the first instance can connect on initial install.
        asg.asg.node.add_dependency(db.db_primary_instance)

        #
        # OUTPUTS
        #

        CfnOutput(
            self,
            "AlbDnsNameOutput",
            description="The DNS name of the application load balancer.",
            value=alb.alb.attr_dns_name
        )
        CfnOutput(
            self,
            "DbClusterEndpointOutput",
            description="The Aurora MySQL writer endpoint. Pre-wired into Drupal's settings.php.",
            value=db.db_cluster.attr_endpoint_address
        )
        CfnOutput(
            self,
            "ElastiCacheClusterEndpointOutput",
            description="The Memcached cluster configuration endpoint. Pre-wired into Drupal's settings.php under $settings['memcache']['servers'].",
            value="{}:{}".format(
                memcached.elasticache_cluster.attr_configuration_endpoint_address,
                memcached.elasticache_cluster.attr_configuration_endpoint_port
            )
        )
        CfnOutput(
            self,
            "FirstUseInstructions",
            description="Instructions for completing the Drupal install",
            value=(
                "Open the site URL and walk through the Drupal install wizard "
                "(Standard profile recommended). Database credentials are "
                "pre-populated in /opt/oe/patterns/drupal/. To enable Memcached "
                "as the cache backend after install, SSM-session into the EC2 "
                "instance and run: cd /var/www/app/drupal && sudo -u www-data "
                "./vendor/bin/drush en memcache -y, then add "
                "$settings['cache']['default'] = 'cache.backend.memcache'; to "
                "sites/default/settings.local.php."
            )
        )

        #
        # CLOUDFORMATION INTERFACE METADATA
        #

        parameter_groups = [
            {
                "Label": {"default": "Notifications"},
                "Parameters": [notification_email_param.logical_id]
            }
        ]
        parameter_groups += alb.metadata_parameter_group()
        parameter_groups += dns.metadata_parameter_group()
        parameter_groups += db_secret.metadata_parameter_group()
        parameter_groups += db.metadata_parameter_group()
        parameter_groups += memcached.metadata_parameter_group()
        parameter_groups += asg.metadata_parameter_group()
        parameter_groups += efs.metadata_parameter_group()
        parameter_groups += vpc.metadata_parameter_group()

        self.template_options.metadata = {
            "OE::Patterns::TemplateVersion": template_version,
            "AWS::CloudFormation::Interface": {
                "ParameterGroups": parameter_groups,
                "ParameterLabels": {
                    notification_email_param.logical_id: {"default": "Notification Email"},
                    **alb.metadata_parameter_labels(),
                    **dns.metadata_parameter_labels(),
                    **db_secret.metadata_parameter_labels(),
                    **db.metadata_parameter_labels(),
                    **memcached.metadata_parameter_labels(),
                    **asg.metadata_parameter_labels(),
                    **efs.metadata_parameter_labels(),
                    **vpc.metadata_parameter_labels()
                }
            }
        }
