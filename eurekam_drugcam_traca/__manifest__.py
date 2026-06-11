# -*- coding: utf-8 -*-
{
    "name": "Eurekam Drugcam Traceability",
    "summary": "Drugcam Traca business fields for Assist workstations (hardware,"
               " cameras, accessories, comments).",
    "description": """
Extension module for the Drugcam installation traceability project.

Extends the ``customer.asset.workstation`` model (provided by the Scalizer
module ``s6r_eurekam_customer_assets``) with 22 business fields required by
the ``drugcam-traca`` application run by Eurekam technicians during each
customer installation.

Sections covered:
- Hardware identification (enclosure type, workstation serial number, date)
- UC (model, PC serial number, CPU version)
- Optical block (type, serial number)
- Camera A and B (type, serial number, objective, cable)
- Scene camera (type, serial number)
- Accessories (mouse, power supply, inox plots)
- Free comments

All modifications are tracked in the chatter (native Odoo audit trail).

Associated client application:
https://github.com/Eurekam-17/Traca_Installation
""",
    "version": "18.0.4.0.0",
    "category": "Customizations",
    "author": "Eurekam",
    "website": "https://eurekam.fr",
    "license": "LGPL-3",
    "depends": [
        "s6r_eurekam_customer_assets",
    ],
    "data": [
        "views/customer_asset_workstation_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
