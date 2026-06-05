# -*- coding: utf-8 -*-
"""Étend customer.asset.workstation (module Scalizer) avec les 22 champs
métier Drugcam Traca.

Tous les champs ont ``tracking=True`` pour être logués dans le chatter de
la fiche poste (audit Odoo natif).

Conventions :
- Nom technique en anglais snake_case (cohérent avec les champs Scalizer
  natifs : software_fedora_version, mac_address, etc.)
- ``string`` (libellé affiché) en français
- Pour les Selections : valeurs techniques en snake_case, libellés en français
- Pour la valeur "3M" qui commence par un chiffre, on utilise "_3m" comme
  valeur technique (Odoo refuse les valeurs Selection commençant par un
  chiffre).
- Pour les types Caméra / UC / Objectif (cf. v18.0.2.0.0) : Many2one vers
  ``product.template`` au lieu de Selection. Permet d'enrichir le catalogue
  d'articles dans Odoo sans toucher au code du module.
"""

from odoo import fields, models


# Domaines de filtrage des Many2one product.template
# Convention de nommage Eurekam : préfixe "PC ", "CAMERA " ou "Caméra ", "Objectif "
DOMAIN_CAMERA = (
    "['|', ('name', '=ilike', 'CAMERA %'), ('name', '=ilike', 'Caméra %')]"
)
DOMAIN_PC = "[('name', '=ilike', 'PC %')]"
DOMAIN_OBJECTIVE = "[('name', '=ilike', 'Objectif %')]"
DOMAIN_MOUSE = "[('name', '=ilike', 'Souris %')]"


class CustomerAssetWorkstation(models.Model):
    _inherit = "customer.asset.workstation"

    # ------------------------------------------------------------------ #
    # Identification matérielle
    # ------------------------------------------------------------------ #
    workstation_serial_number = fields.Char(
        string="N° de série équipement",
        tracking=True,
        help="Numéro de série interne Eurekam (format AB000001).",
    )
    workstation_type = fields.Selection(
        selection=[
            ("iso_jce", "Iso JCE"),
            ("iso_sieve", "Iso Sieve"),
            ("iso_eurobio", "Iso Eurobio"),
            ("iso_getinge", "Iso Getinge"),
            ("hotte_faster", "Hotte Faster"),
            ("hotte_thermofisher", "Hotte Thermofisher"),
            ("hotte_ads", "Hotte ADS"),
            ("hotte_berner", "Hotte Berner"),
            ("autres", "Autres"),
        ],
        string="Type d'enceinte / hotte",
        tracking=True,
    )
    installation_date = fields.Date(
        string="Date d'installation",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # UC
    # ------------------------------------------------------------------ #
    uc_model = fields.Many2one(
        comodel_name="product.template",
        string="Type UC",
        domain=DOMAIN_PC,
        tracking=True,
        help="Référence de l'UC dans le catalogue d'articles Odoo "
             "(filtre sur préfixe 'PC ').",
    )
    pc_serial_number = fields.Char(
        string="N° de série PC",
        tracking=True,
        help="Numéro de série du PC issu de dmidecode -t system.",
    )
    cpu_version = fields.Char(
        string="Version CPU",
        tracking=True,
        help="Référence CPU issue de dmidecode -s processor-version.",
    )

    # ------------------------------------------------------------------ #
    # Bloc optique
    # ------------------------------------------------------------------ #
    optical_block_type = fields.Selection(
        selection=[
            ("sortie_droite", "Sortie droite"),
            ("sortie_laterale", "Sortie latérale"),
            ("democom", "Democom"),
        ],
        string="Type de bloc optique",
        tracking=True,
    )
    optical_block_serial = fields.Char(
        string="N° de série bloc optique",
        tracking=True,
        help="Numéro de série interne Eurekam (format 010001).",
    )

    # ------------------------------------------------------------------ #
    # Caméra A (plus petit S/N parmi les 2 caméras détectées)
    # ------------------------------------------------------------------ #
    camera_a_model = fields.Many2one(
        comodel_name="product.template",
        string="Type caméra A",
        domain=DOMAIN_CAMERA,
        tracking=True,
        help="Référence de la caméra dans le catalogue Odoo "
             "(filtre sur préfixe 'CAMERA ' ou 'Caméra ').",
    )
    camera_a_serial = fields.Char(
        string="N° caméra A",
        tracking=True,
    )
    camera_a_objective = fields.Many2one(
        comodel_name="product.template",
        string="Type objectif caméra A",
        domain=DOMAIN_OBJECTIVE,
        tracking=True,
        help="Référence de l'objectif dans le catalogue Odoo "
             "(filtre sur préfixe 'Objectif ').",
    )
    camera_a_cable = fields.Selection(
        selection=[
            ("fire_wire", "FIRE WIRE"),
            ("alysium", "ALYSIUM"),
            ("alysium_v2", "ALYSIUM V2"),
            ("alysium_blinde_teli", "ALYSIUM BLINDÉ POUR TELI"),
            ("alysium_blinde_alvium", "ALYSIUM BLINDÉ POUR ALVIUM"),
        ],
        string="Type de câble caméra A",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Caméra B (plus grand S/N)
    # ------------------------------------------------------------------ #
    camera_b_model = fields.Many2one(
        comodel_name="product.template",
        string="Type caméra B",
        domain=DOMAIN_CAMERA,
        tracking=True,
    )
    camera_b_serial = fields.Char(
        string="N° caméra B",
        tracking=True,
    )
    camera_b_objective = fields.Many2one(
        comodel_name="product.template",
        string="Type objectif caméra B",
        domain=DOMAIN_OBJECTIVE,
        tracking=True,
    )
    camera_b_cable = fields.Selection(
        selection=[
            ("fire_wire", "FIRE WIRE"),
            ("alysium", "ALYSIUM"),
            ("alysium_v2", "ALYSIUM V2"),
            ("alysium_blinde_teli", "ALYSIUM BLINDÉ POUR TELI"),
            ("alysium_blinde_alvium", "ALYSIUM BLINDÉ POUR ALVIUM"),
        ],
        string="Type de câble caméra B",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Caméra de scène
    # ------------------------------------------------------------------ #
    scene_camera_model = fields.Many2one(
        comodel_name="product.template",
        string="Type caméra de scène",
        domain=DOMAIN_CAMERA,
        tracking=True,
        help="Référence de la caméra de scène dans le catalogue Odoo "
             "(même filtre que les caméras A/B).",
    )
    scene_camera_serial = fields.Char(
        string="N° caméra de scène",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Accessoires
    # ------------------------------------------------------------------ #
    mouse_model = fields.Many2one(
        comodel_name="product.template",
        string="Type de souris",
        domain=DOMAIN_MOUSE,
        tracking=True,
        help="Référence de la souris dans le catalogue Odoo "
             "(filtre sur préfixe 'Souris ').",
    )
    power_supply_type = fields.Selection(
        selection=[
            ("c5_120w", "C5 120W"),
            ("fsp_120w", "FSP 120W"),
            ("meanwell_80w", "MEANWELL 80W"),
            ("cwt_120w", "CWT 120W"),
            ("mean_well_120w", "MEAN WELL 120W"),
        ],
        string="Bloc d'alimentation",
        tracking=True,
    )
    inox_plot_type = fields.Selection(
        selection=[
            ("lohmann", "Lohmann"),
            # Préfixe '_' obligatoire : Odoo refuse les valeurs Selection
            # commençant par un chiffre.
            ("_3m", "3M"),
            # Choix explicite "Aucun" : poste sans plots inox. Distinct de la
            # valeur vide (False = champ non renseigné).
            ("aucun", "Aucun"),
        ],
        string="Plots inox",
        tracking=True,
    )

    # ------------------------------------------------------------------ #
    # Texte libre
    # ------------------------------------------------------------------ #
    comments = fields.Text(
        string="Commentaires",
        tracking=True,
        help="Notes libres sur l'installation de ce poste.",
    )
