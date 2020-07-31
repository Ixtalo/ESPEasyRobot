
# ESPEasy Robot
ASZ, 12/2019

Automate tasks for ESPEasy, e.g., downloading of config files from multiple ESPEasy instances. 


## ESPEasy Download Robot
Automatically download ESPEasy config files.

Manually downloading the configuration of a couple of ESPEasy instances
can be tedious. This script automates this process.
First, it asks for a dnsmasqd leases file to collect the IP addresses
of ESP instances.
Then it continuously probes for awake ESP instances.
Then it downloads all files with HTTP GET.

