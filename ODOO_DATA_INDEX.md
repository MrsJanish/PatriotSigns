# Odoo Data Export Index

> **Generated:** 2025-12-23  
> **Total Files:** 487 CSV exports  
> **Purpose:** Reference index for understanding old Odoo database structure

---

## Sign-Related Models (Primary)

| Model | Records | Description |
|-------|---------|-------------|
| `x_sign_types` | 635 | Master sign type definitions per project |
| `x_sign_categories` | 19 | Sign category classifications (PAN, DCHA, PLQ, etc.) |
| `x_sign_sub_types` | 127 | Sign sub-type templates (Rm Num, Directional, etc.) |
| `x_install_instance` | 1,416 | Individual sign installations with locations |
| `x_dimensions` | 216 | Dimension lookup table (8x6, 10x12, etc.) |
| `x_defined_locations` | 1,506 | Room/location definitions per project |
| `x_sign_schedule` | 3 | Sign schedule documents |

---

## Model: x_sign_categories

**Purpose:** Global sign category classifications

| Key Field | Description |
|-----------|-------------|
| `id` | Primary key |
| `x_name` | Category code (PAN, PAN_Bk, DCHA, etc.) |
| `x_studio_display_name` | Full name (Panel / ADA, Panel Blank Backers) |
| `x_studio_color` | Kanban color code |
| `x_active` | Is active |

**Sample Categories:**
- `PAN` = Panel / ADA
- `PAN_Bk` = Panel Blank Backers
- `DCHA` = Directional Channel Letters (?) 
- `PLQ` = Plaques

---

## Model: x_sign_sub_types

**Purpose:** Template definitions for sign variations within categories

| Key Field | Description |
|-----------|-------------|
| `id` | Primary key |
| `x_name` | Sub-type code (CUSTOM_Directional, Cast Alum Plaque) |
| `x_studio_sign_category` | FK → x_sign_categories.id |
| `x_studio_sign_subtype_display` | Full display name |
| `x_studio_default_copy_lines` | FK → default copy line templates |
| `x_studio_sign_types` | Many2many → x_sign_types.id |
| `x_studio_setup_status` | COMPLETED, etc. |

**Relationship:** Links sign types to their reusable templates

---

## Model: x_sign_types

**Purpose:** Project-specific sign type definitions (the main sign data model)

### Identification Fields
| Field | Description |
|-------|-------------|
| `id` | Primary key |
| `x_name` | Sign type ID within project (1, 3_old, A, etc.) |
| `x_studio_sign_type` | Display number |
| `x_studio_sign_type_label` | Full label (e.g., "1 \| Rm Num, Insert") |

### Project Linkage
| Field | Description |
|-------|-------------|
| `x_studio_project` | FK → project.project.id |
| `x_studio_project_alias` | Project short name |
| `x_studio_generated_project` | FK → generated project |

### Category & Sub-Type
| Field | Description |
|-------|-------------|
| `x_studio_sign_category` | FK → x_sign_categories.id |
| `x_studio_sign_subtype` | FK → x_sign_sub_types.id |
| `x_studio_sign_subtype_display` | Display name from sub-type |
| `x_studio_sign_category_color` | Color from category |

### Dimensions
| Field | Description |
|-------|-------------|
| `x_studio_dimensions` | FK → x_dimensions.id |
| `x_studio_height_in` | Height in inches |
| `x_studio_width_in` | Width in inches |
| `x_studio_height_ft` | Height in feet |
| `x_studio_width_ft` | Width in feet |
| `x_studio_depththickness` | Depth/thickness |
| `x_studio_sq_in` | Computed square inches |
| `x_studio_is_round` | Boolean for round signs |
| `x_studio_diameter` | Diameter if round |
| `x_studio_size_display` | Display string (e.g., "8 x 6") |

### Quantity Tracking
| Field | Description |
|-------|-------------|
| `x_studio_ss_qty` | Sign schedule quantity |
| `x_studio_item_qty` | Item quantity |
| `x_studio_unit_pc_quantity` | Units per piece |
| `x_studio_qty_source` | Source of quantity data |
| `x_studio_variant_qty` | Variant quantity |
| `x_studio_component_qty` | Component quantity |
| `x_studio_sign_type_qty` | Sign type quantity |

### Pricing & Costing
| Field | Description |
|-------|-------------|
| `x_studio_unit_cost` | Unit cost |
| `x_studio_unit_price` | Unit price |
| `x_studio_bid_unit_price` | Bid unit price |
| `x_studio_install_rate` | Installation rate |
| `x_studio_install_rate_per_piece` | Install rate per piece |
| `x_studio_currency_id` | Currency reference |

### Status & Stage
| Field | Description |
|-------|-------------|
| `x_studio_stage` | Current stage |
| `x_studio_stage_id` | FK → stage record |
| `x_studio_kanban_state` | Kanban state |
| `x_active` | Is active |
| `x_studio_project_update_stage` | Project update stage |

### Relationships
| Field | Description |
|-------|-------------|
| `x_studio_install_instances` | One2many → x_install_instance |
| `x_studio_variant_of_sign_type` | FK → parent sign type (for variants) |
| `x_studio_component_of_sign_type` | FK → parent (for components) |
| `x_studio_replaced_by` | FK → replacement sign type |
| `x_studio_sign_type_backer` | FK → backer sign type |
| `x_studio_supplier` | FK → supplier |

### Copy/Content
| Field | Description |
|-------|-------------|
| `x_studio_default_copy_lines` | Default copy line templates |
| `x_studio_sign_type_custom_copy` | Has custom copy |
| `x_studio_letters` | Letter content |
| `x_studio_letter_count` | Letter count |
| `x_studio_letter_height_in` | Letter height in inches |

### Flags
| Field | Description |
|-------|-------------|
| `x_studio_is_backer` | Is a backer sign |
| `x_studio_added_post_bid` | Added after bid |
| `x_studio_whos_court` | Whose court (responsibility) |
| `x_studio_office_use` | Office use only |

---

## Model: x_install_instance

**Purpose:** Individual sign installation records with specific locations

### Identification
| Field | Description |
|-------|-------------|
| `id` | Primary key |
| `x_name` | Instance name/ID |
| `x_studio_sign_markid` | Sign mark/ID on plans |
| `x_studio_mark` | Mark number |

### Sign Type Reference
| Field | Description |
|-------|-------------|
| `x_studio_sign_type` | FK → x_sign_types.id |
| `x_studio_sign_type_label` | Label from sign type |
| `x_studio_sign_type_size` | Size from sign type |
| `x_studio_sign_type_dimensions` | Dimensions from sign type |
| `x_studio_sign_category` | Category from sign type |

### Location Hierarchy
| Field | Description |
|-------|-------------|
| `x_studio_project` | FK → project.project.id |
| `x_studio_project_alias` | Project short name |
| `x_studio_install_location` | FK → x_defined_locations.id |
| `x_studio_parent_location_display` | Parent location display |
| `x_studio_1st_gen_parent_loc` | First level parent |
| `x_studio_2nd_gen_parent_loc` | Second level parent |
| `x_studio_3rd_gen_parent_loc` | Third level parent |
| `x_studio_4th_gen_parent_loc` | Fourth level parent |
| `x_studio_parent_path` | Full parent path |
| `x_studio_current_loc_` | Current location ID |
| `x_studio_current_loc_name` | Current location name |

### Room Details
| Field | Description |
|-------|-------------|
| `x_studio_rm_fp` | Room from floor plans |
| `x_studio_arch_rm_num` | Architectural room number |
| `x_studio_rm_name_fp` | Room name from floor plans |
| `x_studio_arch_rm_name` | Architectural room name |
| `x_studio_door_id` | Door ID |

### Copy Content
| Field | Description |
|-------|-------------|
| `x_studio_copy_line_1` | Copy line 1 |
| `x_studio_copy_line_2` | Copy line 2 |
| `x_studio_copy_line_3` | Copy line 3 |
| `x_studio_copy_line_4` | Copy line 4 |
| `x_studio_copy_line_5` | Copy line 5 |
| `x_studio_custom_copy` | Has custom copy |
| `x_studio_copy_line_string` | Full copy string |
| `x_studio_default_copy_lines` | Default copy templates |

### Status & Sequencing
| Field | Description |
|-------|-------------|
| `x_studio_stage_id` | Current stage |
| `x_studio_approved` | Is approved |
| `x_studio_quality_check` | Quality checked |
| `x_studio_install_sequence` | Install sequence number |
| `x_studio_production_sort` | Production sort order |
| `x_studio_prepost_bid` | Pre/post bid indicator |

---

## Model: x_dimensions

**Purpose:** Reusable dimension lookup table

| Key Field | Description |
|-----------|-------------|
| `id` | Primary key |
| `x_name` | Display name (e.g., "8 x 8", "6 x 4") |
| `x_studio_width_in` | Width in inches |
| `x_studio_height_in` | Height in inches |
| `x_studio_width_ft` | Width in feet |
| `x_studio_height_ft` | Height in feet |
| `x_studio_square_inches` | Computed area |
| `x_studio_can_be_round` | Can be round shape |
| `x_studio_dim_display_by_inch` | Display by inches |
| `x_studio_dim_display_by_feetinch` | Display by feet/inches |

---

## Model: x_defined_locations

**Purpose:** Project-specific location/room definitions

### Identification
| Field | Description |
|-------|-------------|
| `id` | Primary key |
| `x_name` | Location display name (e.g., "S120 [1038]") |
| `x_studio_location_num` | Location number |
| `x_studio_location_num_id` | Location numeric ID |
| `x_studio_location_internal_id` | Internal ID |

### Project Reference
| Field | Description |
|-------|-------------|
| `x_studio_project` | FK → project.project.id |
| `x_studio_project_alias` | Project short name |
| `x_studio_project_company_name` | Company name |
| `x_studio_project_owner` | Project owner |

### Location Type & Hierarchy
| Field | Description |
|-------|-------------|
| `x_studio_location_type` | Location type (RM, AREA, etc.) |
| `x_studio_parent_location` | FK → parent location |
| `x_studio_level_floor_num` | Floor/level number |
| `x_studio_jobsite_location` | Jobsite reference |
| `x_studio_jobsite_address` | Physical address |
| `x_studio_jobsite` | Jobsite name |

### Room Details
| Field | Description |
|-------|-------------|
| `x_studio_room_number` | Room number |
| `x_studio_room_name_arch_ref` | Architectural room name |
| `x_studio_room_name_floor_plan_ref` | Floor plan room name |
| `x_studio_og_room_number` | Original room number |
| `x_studio_room_rename` | Room renamed |
| `x_studio_room_renumber` | Room renumbered |
| `x_studio_is_revision` | Is a revision |
| `x_studio_revision_of` | FK → original location |

### Relationships
| Field | Description |
|-------|-------------|
| `x_studio_sign_types` | Many2many → x_sign_types |
| `x_studio_install_instances` | One2many → x_install_instance |
| `x_studio_mu_comments` | Related comments |

---

## Other Business Models

| Model | Records | Description |
|-------|---------|-------------|
| `project.project` | 21 | Odoo projects |
| `crm.lead` | 0 | CRM leads (empty) |
| `sale.order` | varies | Sales orders |
| `purchase.order` | varies | Purchase orders |
| `product.product` | varies | Products |
| `res.partner` | varies | Contacts/companies |

---

## Relationship Diagram

```
project.project (21)
    └── x_sign_types (635)
            ├── x_sign_categories (19)
            ├── x_sign_sub_types (127)
            ├── x_dimensions (216)
            └── x_install_instance (1,416)
                    └── x_defined_locations (1,506)
```

---

## Key Insights

1. **Project-Scoped Sign Types**: Sign types are linked to projects via `x_studio_project` - same type name can mean different things across projects

2. **Three-Level Category System**:
   - Category (x_sign_categories) - broad classification (Panel, Plaque, etc.)
   - Sub-Type (x_sign_sub_types) - templates within category
   - Sign Type (x_sign_types) - project-specific instance

3. **Location Hierarchy**: Defined locations support parent-child relationships with up to 4 levels of nesting

4. **Dimension Lookup**: Dimensions are stored as a reusable lookup table, preventing "6x8" vs "6 x 8" inconsistencies

5. **Install Instance = Physical Sign**: Each install instance represents ONE physical sign at ONE location with specific copy content

6. **Extensive Status Tracking**: Multiple stage/status fields track sign through bidding → production → installation

---

## Files Categorized by Function

### Signs & Installation (13 files)
- x_sign_types.csv, x_sign_types_stage.csv, x_sign_types_tag.csv
- x_sign_categories.csv, x_sign_categories_tag.csv
- x_sign_sub_types.csv, x_sign_sub_types_tag.csv
- x_sign_schedule.csv, x_sign_schedule_stage.csv
- x_install_instance.csv, x_install_instance_stage.csv, x_install_instance_tag.csv
- x_install_instances.csv, x_install_instances_stage.csv

### Locations (4 files)
- x_defined_locations.csv, x_defined_locations_stage.csv, x_defined_locations_tag.csv
- x_dimensions.csv

### Projects & Change Orders (8 files)
- project.project.csv, project.task.csv, project.milestone.csv
- x_change_order.csv, x_change_order_stage.csv
- x_change_order_item.csv, x_change_order_item_stage.csv
- x_schedule_of_values.csv

### Bidding (4 files)
- x_bidding_gc.csv, x_bidding_gc_stage.csv, x_bidding_gc_tag.csv
- x_bidding_gcs.csv, x_bidding_gcs_stage.csv

### Core Odoo (varies)
- account.* - Accounting
- crm.* - CRM
- hr.* - Human resources
- mrp.* - Manufacturing
- product.* - Products
- purchase.* - Purchasing
- sale.* - Sales
- stock.* - Inventory
