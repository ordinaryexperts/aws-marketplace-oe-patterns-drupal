# gen-plf.py
# ----------
#
# Generates a row suitable for submitting to AWS Marketplace in their Product Load Form

import csv
import yaml

column_headers = open("/code/scripts/gen-plf-column-headers.txt").read().rstrip().split("\t")

plf_config = yaml.load(
    open("/code/plf_config.yaml"),
    Loader=yaml.SafeLoader
)

plf_values = {}

for header in column_headers:
    if header in plf_config:
        plf_values[header] = plf_config[header]
    else:
        plf_values[header] = ""
    # print(header)

with open('/code/pfl.csv', 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=column_headers)
    writer.writeheader()
    writer.writerow(plf_values)

print("PLF row saved to 'pfl.csv'")
