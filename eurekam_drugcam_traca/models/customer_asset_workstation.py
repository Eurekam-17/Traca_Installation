# -*- coding: utf-8 -*-
"""Extends customer.asset.workstation (Scalizer module) with the 22 Drugcam
Traca business fields.

All fields have ``tracking=True`` so changes are logged in the workstation
record's chatter (native Odoo audit trail).

Conventions:
- Technical names in English snake_case (consistent with native Scalizer fields:
  software_fedora_version, mac_address, etc.)
- ``string`` (displayed label) in English; French translations in i18n/fr.po
- For Selections: technical values in snake_case, labels in English
- For the "3M" value that starts with a digit, we use "_3m" as the technical
  value (Odoo rejects Selection values starting with a digit).
- For Camera / UC / Objective types (cf. v18.0.2.0.0): Many2one to
  ``product.template`` instead of Selection. Allows enriching the product
  catalog in Odoo without touching the module code.
"""

from odoo import fields, models


# Many2one product.template filter domains
# Eurekam naming convention: prefix "PC ", "CAMERA " or "Caméra ", "Objectif "
DOMAIN_CAMERA = (
    "['|', ('name', '=ilike', 'CAMERA %'), ('name', '=ilike', 'Caméra %')]"
)
DOMAIN_PC = "[('name', '=ilike', 'PC %')]"
DOMAIN_OBJECTIVE = "[('name', '=ilike', 'Objectif %')]"
DOMAIN_MOUSE = "[('name', '=ilike', 'Souris %')]"


class CustomerAssetWorkstation(models.Model):
    _inherit = "customer.asset.workstation"

    # ------------------------------------------------------------------ #
    # Hardware identification
    # ------------------------------------------------------------------ #
    workstation_serial_number = fields.Char(
        string="Workstation Serial Number",
        tracking=True,
        help="Eurekam internal serial number (format AB000001).",
    )
    workstation_type = fields.Selection(
        selection=[
            ("iso_jce", "Iso JCE"),
            ("iso_sieve", "Iso Sieve"),
            ("iso_eurobio", "Iso Eurobio"),
            ("iso_getinge", "Iso Getinge"),
            ("hotte_faster", "Faster Hood"),
            ("hotte_thermofisher", "Thermofisher Hood"),
            ("hotte_ads", "ADS Hood"),
            ("hotte_berner", "Berner Hood"),
            ("autres", "Other"),
        ],
        string="Enclosure / Hood Type",
        tracking=True,
    )
    installation_date = fields.Date(
        string="Installation Date",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # UC (workstation unit)
    # ------------------------------------------------------------------ #
    uc_model = fields.Many2one(
        comodel_name="product.template",
        string="UC Type",
        domain=DOMAIN_PC,
        tracking=True,
        help="UC reference in the Odoo product catalog (filtered by 'PC ' prefix).",
    )
    pc_serial_number = fields.Char(
        string="PC Serial Number",
        tracking=True,
        help="PC serial number from dmidecode -t system.",
    )
    cpu_version = fields.Char(
        string="CPU Version",
        tracking=True,
        help="CPU reference from dmidecode -s processor-version.",
    )

    # ------------------------------------------------------------------ #
    # Optical block
    # ------------------------------------------------------------------ #
    optical_block_type = fields.Selection(
        selection=[
            ("sortie_droite", "Right Exit"),
            ("sortie_laterale", "Side Exit"),
            ("democom", "Democom"),
        ],
        string="Optical Block Type",
        tracking=True,
    )
    optical_block_serial = fields.Char(
        string="Optical Block Serial Number",
        tracking=True,
        help="Eurekam internal serial number (format 010001).",
    )

    # ------------------------------------------------------------------ #
    # Camera A (lowest S/N among the 2 detected cameras)
    # ------------------------------------------------------------------ #
    camera_a_model = fields.Many2one(
        comodel_name="product.template",
        string="Camera A Type",
        domain=DOMAIN_CAMERA,
        tracking=True,
        help="Camera reference in the Odoo product catalog "
             "(filtered by 'CAMERA ' or 'Caméra ' prefix).",
    )
    camera_a_serial = fields.Char(
        string="Camera A Serial Number",
        tracking=True,
    )
    camera_a_objective = fields.Many2one(
        comodel_name="product.template",
        string="Camera A Objective Type",
        domain=DOMAIN_OBJECTIVE,
        tracking=True,
        help="Objective reference in the Odoo product catalog "
             "(filtered by 'Objectif ' prefix).",
    )
    camera_a_cable = fields.Selection(
        selection=[
            ("fire_wire", "FIRE WIRE"),
            ("alysium", "ALYSIUM"),
            ("alysium_v2", "ALYSIUM V2"),
            ("alysium_blinde_teli", "ALYSIUM SHIELDED FOR TELI"),
            ("alysium_blinde_alvium", "ALYSIUM SHIELDED FOR ALVIUM"),
        ],
        string="Camera A Cable Type",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Camera B (highest S/N)
    # ------------------------------------------------------------------ #
    camera_b_model = fields.Many2one(
        comodel_name="product.template",
        string="Camera B Type",
        domain=DOMAIN_CAMERA,
        tracking=True,
    )
    camera_b_serial = fields.Char(
        string="Camera B Serial Number",
        tracking=True,
    )
    camera_b_objective = fields.Many2one(
        comodel_name="product.template",
        string="Camera B Objective Type",
        domain=DOMAIN_OBJECTIVE,
        tracking=True,
    )
    camera_b_cable = fields.Selection(
        selection=[
            ("fire_wire", "FIRE WIRE"),
            ("alysium", "ALYSIUM"),
            ("alysium_v2", "ALYSIUM V2"),
            ("alysium_blinde_teli", "ALYSIUM SHIELDED FOR TELI"),
            ("alysium_blinde_alvium", "ALYSIUM SHIELDED FOR ALVIUM"),
        ],
        string="Camera B Cable Type",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Scene camera
    # ------------------------------------------------------------------ #
    scene_camera_model = fields.Many2one(
        comodel_name="product.template",
        string="Scene Camera Type",
        domain=DOMAIN_CAMERA,
        tracking=True,
        help="Scene camera reference in the Odoo product catalog "
             "(same filter as cameras A/B).",
    )
    scene_camera_serial = fields.Char(
        string="Scene Camera Serial Number",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Accessories
    # ------------------------------------------------------------------ #
    mouse_model = fields.Many2one(
        comodel_name="product.template",
        string="Mouse Type",
        domain=DOMAIN_MOUSE,
        tracking=True,
        help="Mouse reference in the Odoo product catalog "
             "(filtered by 'Souris ' prefix).",
    )
    power_supply_type = fields.Selection(
        selection=[
            ("c5_120w", "C5 120W"),
            ("fsp_120w", "FSP 120W"),
            ("meanwell_80w", "MEANWELL 80W"),
            ("cwt_120w", "CWT 120W"),
            ("mean_well_120w", "MEAN WELL 120W"),
        ],
        string="Power Supply",
        tracking=True,
    )
    inox_plot_type = fields.Selection(
        selection=[
            ("lohmann", "Lohmann"),
            # '_' prefix required: Odoo rejects Selection values starting with a digit.
            ("_3m", "3M"),
            # Explicit "None" choice: workstation without inox plots.
            # Distinct from the empty value (False = field not filled in).
            ("aucun", "None"),
        ],
        string="Inox Plots",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Free text
    # ------------------------------------------------------------------ #
    comments = fields.Text(
        string="Comments",
        tracking=True,
        help="Free notes about this workstation installation.",
    )
