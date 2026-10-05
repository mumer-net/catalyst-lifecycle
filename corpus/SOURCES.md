# Where these outputs come from

Every file here is real `show` output from a Catalyst switch, taken unchanged from the test data of two open-source parser projects. Both are under the Apache License 2.0 (copy in [LICENSE-APACHE-2.0](LICENSE-APACHE-2.0)). Some serial numbers were already masked or replaced by those projects.

| Folder | File | Copied from |
| --- | --- | --- |
| genie-c4507re-vss | show_inventory.txt | genieparser `src/genie/libs/parser/iosxe/tests/ShowInventory/cli/equal/golden_output_3_output.txt` |
| genie-c9407r | show_inventory.txt | genieparser `src/genie/libs/parser/iosxe/tests/ShowInventory/cli/equal/golden_output_5_output.txt` |
| genie-c4507re-sup7le | show_module.txt | genieparser `src/genie/libs/parser/iosxe/cat4k/tests/ShowModule/cli/equal/golden_output_c4507_output.txt` |
| ntc-c4507re-vss-standby | show_module.txt | ntc-templates `tests/cisco_ios/show_module/cisco_ios_show_module_02.raw` |
| genie-c4507re-xe-3.3 | show_version.txt | genieparser `src/genie/libs/parser/iosxe/tests/ShowVersion/cli/equal/golden_output_c4507_output.txt` |
| genie-c4510re-xe-3.4 | show_version.txt | genieparser `src/genie/libs/parser/iosxe/tests/ShowVersion/cli/equal/golden_output_1_output.txt` |
| genie-c4507re-xe-3.6 | show_version.txt | genieparser `src/genie/libs/parser/iosxe/tests/ShowVersion/cli/equal/golden_output_9_output.txt` |
| genie-c4507r-ios-12.2 | show_version.txt | genieparser `src/genie/libs/parser/ios/tests/ShowVersion/cli/equal/golden_output_ios_2_output.txt` |

- genieparser: https://github.com/CiscoTestAutomation/genieparser, commit `9a2df6a801c50bcf25e1ca49ffd82b2222da8695`. Copyright Cisco Systems, Inc.
- ntc-templates: https://github.com/networktocode/ntc-templates, commit `d86d09fa105ee2a432795022e7df04737c65dd28`. Copyright 2015 Jason Edelman, Network to Code, LLC.

Left out: ntc-templates' other 4500 `show module` samples (`cisco_ios_show_module2.raw` and `3.raw`). Their part numbers start with `AS-T` (for example `AS-T45-SUP7-E`), which isn't a Cisco part number, so they look edited.
