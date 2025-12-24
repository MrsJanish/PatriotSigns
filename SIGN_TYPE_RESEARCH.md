# Sign Type Data Model - Research & Best Practices

> **Purpose:** Define the complete data structure for sign types in Odoo  
> **Based on:** Industry research, your Workflow.drawio, and current `cc.sign.type` model

---

## Current State Analysis

Your current `cc.sign.type` model has **basic fields**:

| Field | Type | Status |
|-------|------|--------|
| `name` | Char | ✅ Have (Sign Type ID) |
| `quantity` | Integer | ✅ Have |
| `length`, `width` | Float | ✅ Have |
| `has_window` | Boolean | ✅ Have |
| `material` | Char | ✅ Have |
| `mounting` | Char | ✅ Have |
| `color` | Char | ✅ Have |
| `notes` | Text | ✅ Have |
| `confirmed` | Boolean | ✅ Have |

**What's Missing:**
- ❌ Sign Category hierarchy
- ❌ Location data (building, floor, room)
- ❌ ADA compliance fields
- ❌ Illumination details
- ❌ Text/copy content
- ❌ Per-sign instance tracking (SignSetID)
- ❌ Bill of Materials / parts breakdown
- ❌ Costing information

---

## Critical Design Principles

### 1. Sign Types are PROJECT-SCOPED

> ⚠️ **Key Insight:** Sign Type "A" in Project 1 is COMPLETELY DIFFERENT from Sign Type "A" in Project 2.

Each architect defines their own sign type naming and specifications. Within a single project, "Type A" is consistent (e.g., always 6x8 room sign), but across projects, the same name can mean totally different things.

**Therefore:** Sign types are children of the project/opportunity, NOT global templates.

```
Project 1 (Hospital)
├── Type A = 6x6 Room ID, ADA
├── Type B = 8x2 Directional
└── Type C = Monument

Project 2 (School)  
├── Type A = 6x8 Room ID, ADA   ← Different from Project 1's "Type A"!
├── Type B = 4x4 Classroom
└── Type C = 12x8 Exterior
```

### 2. ALL Inputs Must Be Standardized

> 🚫 **No Free Text for Critical Fields** - Prevent "6 in." vs "6"" vs "6" conflicts

| Field Type | ❌ Bad (Free Text) | ✅ Good (Constrained) |
|------------|-------------------|----------------------|
| Dimensions | `"6 x 8"` text | `length=6.0`, `width=8.0` (Float) |
| Material | `"Alum"`, `"Aluminum"`, `"AL"` | Selection dropdown |
| Mounting | `"wall mount"`, `"Wall"`, `"WM"` | Selection dropdown |
| Finish | `"Matte"`, `"matte"`, `"MT"` | Selection dropdown |
| ADA | `"yes"`, `"Y"`, `"ADA"` | Boolean checkbox |

**Implementation:** Use `Selection` fields, `Many2one` lookups, `Float` for numbers, `Boolean` for yes/no. Reserve `Char`/`Text` only for truly free-form content (names, notes, copy text).

### 3. Extensible Sign Categories

Users must be able to add new sign categories when encountering unfamiliar sign types, but using the same standardized input structure.

---

## Recommended Data Model

### Hierarchy Overview

```
Project/Opportunity
└── Sign Type (project-specific: "A", "B", "SN-1", etc.)
    ├── Specifications (dimensions, material, mounting, ADA, etc.)
    ├── Sign Instances (each physical sign with location)
    │   └── Location (Building, Floor, Room, Wall)
    └── Sign Parts (Backplate, Letters, Pictograms) [FUTURE - for production]
```

### Master Reference Tables (Global)

These are reusable across all projects:
- **Sign Categories** (Panel, Monument, Pylon, Channel Letters, etc.)
- **Materials** (Aluminum, Acrylic, PVC, etc.)
- **Finishes** (Matte, Satin, Gloss, Brushed, etc.)
- **Mounting Methods** (Wall, Projecting, Ceiling, Post, etc.)

---

## Model 1: `sign.category`

**Purpose:** Group sign types into logical categories for organization and filtering.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | Char | ✅ | Category name (e.g., "ADA Room Signs", "Wayfinding", "Exterior") |
| `code` | Char | | Short code (e.g., "ADA", "WF", "EXT") |
| `description` | Text | | Category description |
| `sign_type_ids` | One2many | | Sign types in this category |
| `is_ada_required` | Boolean | | Default ADA compliance for this category |
| `color` | Integer | | Kanban color for visual grouping |

**Common Categories:**
- Room Identification (ADA)
- Directional / Wayfinding
- Regulatory / Safety
- Exterior / Monument
- Interior Décor
- Parking / Traffic
- Digital / Electronic

---

## Model 2: `sign.type` (Enhanced)

**Purpose:** Master definition of a sign type within a project.

### Identification Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | Char | ✅ | Sign Type ID (e.g., "SN-1", "RID-1") |
| `opportunity_id` | Many2one | ✅ | Link to project/opportunity |
| `category_id` | Many2one | | Sign category |
| `description` | Text | | Full description |

### Dimensions Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `length` | Float | | Length in inches |
| `width` | Float | | Width in inches |
| `depth` | Float | | Depth/thickness in inches |
| `dimensions_display` | Char | Computed | Display string "W x H x D" |

### Physical Specifications

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `substrate_id` | Many2one | | Link to product (material) |
| `substrate_text` | Char | | Manual entry if no product |
| `finish` | Selection | | Matte, Satin, Gloss, etc. |
| `finish_color` | Char | | Color name or code |
| `has_window` | Boolean | | Has window/cutout |
| `window_dimensions` | Char | | Window size if applicable |

### Mounting Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mounting_method` | Selection | | Wall, Post, Ceiling, Projecting, Freestanding |
| `mounting_hardware` | Char | | Hardware specs (standoffs, screws, etc.) |
| `mounting_height_aff` | Float | | Height above finished floor (inches) |
| `mounting_notes` | Text | | Special mounting instructions |

### ADA Compliance Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `is_ada` | Boolean | | Is this an ADA sign? |
| `has_tactile` | Boolean | | Raised tactile characters |
| `has_braille` | Boolean | | Braille translation |
| `has_pictogram` | Boolean | | Includes pictogram |
| `pictogram_type` | Char | | Type of pictogram if applicable |
| `contrast_verified` | Boolean | | 70% contrast ratio verified |
| `non_glare_finish` | Boolean | | Non-glare finish applied |

### Typography Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `font_family` | Char | | Primary font (e.g., "Helvetica", "Futura") |
| `font_style` | Selection | | Regular, Bold, Italic |
| `text_case` | Selection | | Upper, Title, Lower, Mixed |
| `character_height` | Float | | Primary text height in inches |
| `secondary_text_height` | Float | | Secondary text height |
| `text_color` | Char | | Text/graphics color |

### Illumination Section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `is_illuminated` | Boolean | | Sign is illuminated |
| `illumination_type` | Selection | | Internal, External, Edge-lit, Halo-lit |
| `power_source` | Selection | | Hardwired, Solar, Battery |
| `voltage` | Char | | Electrical specs (e.g., "120V", "12V DC") |
| `led_color` | Char | | LED color temperature/type |

### Quantity & Instances

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `quantity` | Integer | | Total count of this sign type |
| `instance_ids` | One2many | | Individual sign instances |
| `instance_count` | Integer | Computed | Count of instances |

### Costing Section (for Estimating)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `estimated_material_cost` | Float | | Material cost per unit |
| `estimated_labor_hours` | Float | | Labor hours per unit |
| `estimated_total` | Float | Computed | Total estimated cost |
| `bom_id` | Many2one | | Link to Bill of Materials (future) |

### Status & Tracking

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `state` | Selection | | Draft, Confirmed, In Production, Complete |
| `confirmed` | Boolean | | Confirmed for schedule |
| `confirmed_by` | Many2one | | User who confirmed |
| `confirmed_date` | Datetime | | When confirmed |

### Bookmarks & Documents

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bookmark_ids` | One2many | | PDF bookmarks for this type |
| `bookmark_count` | Integer | Computed | Count of bookmarks |
| `spec_sheet_ids` | Many2many | | Attached specification documents |

---

## Model 3: `sign.instance` (NEW)

**Purpose:** Track each individual physical sign with its specific location.

Based on your Workflow.drawio breakdown:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | Char | Computed | Auto-generated (e.g., "SN-1 #001") |
| `sign_type_id` | Many2one | ✅ | Parent sign type |
| `sequence` | Integer | | Instance number within type |

### Location Fields (from your drawio)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `building` | Char | | Building name/number |
| `floor` | Char | | Floor level |
| `area` | Char | | Area within floor |
| `room_from` | Char | | From room number (on plans) |
| `room_to` | Char | | To room (for directional) |
| `room_actual` | Char | | Actual room name/number |
| `door_number` | Char | | Adjacent door number |
| `wall_location` | Selection | | Latch side, Strike side, Above, etc. |
| `specific_wall` | Char | | Wall identifier |

### Copy Content

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `copy_line_1` | Char | | Primary text content |
| `copy_line_2` | Char | | Secondary text |
| `copy_line_3` | Char | | Additional text |
| `pictogram_code` | Char | | Pictogram reference |
| `arrow_direction` | Selection | | None, Up, Down, Left, Right, Up-Left, etc. |

### Bidding & Phasing

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `bid_package` | Selection | | Base Bid, Alt 1, Alt 2, etc. |
| `phase` | Char | | Construction phase |
| `bid_line_item` | Char | | Separate bid line if required |

### Status

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `state` | Selection | | Draft, Approved, In Production, Installed |
| `installed_date` | Date | | When installed |
| `installed_by` | Many2one | | Install technician |
| `photo_ids` | Many2many | | Install photos |

---

## Model 4: `sign.part` (Future - for Production)

**Purpose:** Break down sign into manufacturable components.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | Char | ✅ | Part name (e.g., "Backplate", "Letters") |
| `sign_type_id` | Many2one | ✅ | Parent sign type |
| `part_type` | Selection | | Panel, Letters, Pictogram, Hardware, etc. |
| `material_id` | Many2one | | Product/material used |
| `quantity` | Float | | Quantity per sign |
| `layer_level` | Integer | | Assembly layer (1=base, 2=middle, etc.) |
| `production_notes` | Text | | Fabrication instructions |

---

## View Recommendations

### 1. Sign Tally View (Current - Enhanced)

**Purpose:** Quick count/tally mode during bid review

**Key Features:**
- Card/tile layout for each sign type
- Large +/- quantity buttons
- Inline dimension editing
- Quick ADA checkbox
- Color-coded by category

### 2. Sign Schedule View (Tree/List)

**Purpose:** Detailed table view matching traditional sign schedules

**Columns to Show:**
| Column | Notes |
|--------|-------|
| Sign Type | Primary identifier |
| Category | Color badge |
| Qty | Editable inline |
| Dimensions | W x H x D |
| Material | Dropdown |
| Mounting | Dropdown |
| ADA | Checkbox + icon |
| Illuminated | Checkbox + icon |
| Est. Cost | Currency |
| Status | Badge |

### 3. Sign Type Form View

**Purpose:** Full detail editing for a sign type

**Page Layout:**
```
┌─────────────────────────────────────────────────┐
│ [Header: Sign Type ID + Category Tag]           │
├─────────────────────────────────────────────────┤
│ TABS:                                           │
│ ┌─────────┬──────────┬─────────┬───────┬──────┐│
│ │ Details │ ADA/Spec │ Costing │ Parts │ Docs ││
│ └─────────┴──────────┴─────────┴───────┴──────┘│
│                                                 │
│ [Details Tab]                                   │
│ ┌─────────────────┬─────────────────┐          │
│ │ Dimensions      │ Physical Specs  │          │
│ │ • Length        │ • Material      │          │
│ │ • Width         │ • Finish        │          │
│ │ • Depth         │ • Color         │          │
│ │ • Has Window    │ • Mounting      │          │
│ └─────────────────┴─────────────────┘          │
│                                                 │
│ [Instances Section - collapsed by default]      │
│ ┌─────────────────────────────────────────────┐│
│ │ Instance | Building | Floor | Room | Status ││
│ │ SN-1 #1  | Main     | 1     | 101  | Draft  ││
│ │ SN-1 #2  | Main     | 1     | 102  | Draft  ││
│ └─────────────────────────────────────────────┘│
│                                                 │
│ [Bookmarks Section - with mini PDF previews]    │
└─────────────────────────────────────────────────┘
```

### 4. Kanban View (by Category or Status)

**Purpose:** Visual project overview

**Kanban Columns:**
- By Category: ADA | Wayfinding | Exterior | Interior
- By Status: Draft | Confirmed | In Production | Complete

---

## Selection Field Options

### `mounting_method` Options
```python
[
    ('wall', 'Wall Mounted'),
    ('projecting', 'Projecting/Flag'),
    ('ceiling', 'Ceiling Hung'),
    ('post', 'Post Mounted'),
    ('freestanding', 'Freestanding'),
    ('monument', 'Monument'),
    ('window', 'Window/Glass'),
]
```

### `finish` Options
```python
[
    ('matte', 'Matte'),
    ('satin', 'Satin'),
    ('gloss', 'Gloss'),
    ('brushed', 'Brushed'),
    ('textured', 'Textured'),
    ('painted', 'Painted'),
    ('woodgrain', 'Woodgrain Laminate'),
]
```

### `illumination_type` Options
```python
[
    ('none', 'Non-Illuminated'),
    ('internal', 'Internally Illuminated'),
    ('external', 'Externally Illuminated'),
    ('edge', 'Edge-Lit'),
    ('halo', 'Halo-Lit'),
    ('channel', 'Channel Letters'),
    ('neon', 'Neon/LED Neon'),
]
```

### `state` Options
```python
[
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('submitted', 'In Submittals'),
    ('approved', 'Approved'),
    ('production', 'In Production'),
    ('complete', 'Complete'),
]
```

### `bid_package` Options
```python
[
    ('base', 'Base Bid'),
    ('alt1', 'Alternate 1'),
    ('alt2', 'Alternate 2'),
    ('alt3', 'Alternate 3'),
    ('additive', 'Additive'),
    ('deductive', 'Deductive'),
]
```

---

## Implementation Priority

### Phase 1 (Now) - Enhanced Sign Type
1. Add `category_id` field with basic categories
2. Add `depth` dimension
3. Add ADA fields (`is_ada`, `has_tactile`, `has_braille`)
4. Add `illumination_type` field
5. Add `state` field with proper workflow
6. Improve Sign Tally UI to show new fields

### Phase 2 (Later) - Sign Instances
1. Create `sign.instance` model
2. Add location fields
3. Add copy/content fields
4. Build instance management UI

### Phase 3 (Future) - Production Integration
1. Create `sign.part` model
2. Link to Odoo MRP Bill of Materials
3. Auto-generate manufacturing orders

---

## Questions for Carter

1. **Categories:** What sign categories do you use most often? (ADA, Wayfinding, Monument, etc.)

2. **Location Tracking:** Do you need to track individual sign locations during bidding, or only after contract?

3. **Content/Copy:** Do you need to store the actual text content for each sign during estimating?

4. **Illumination:** How often do you bid illuminated signs? Is this a common field?

5. **Costing:** Do you want per-unit cost estimates at the sign type level, or is that handled separately?

6. **Alternates:** How do you currently handle bid alternates? Separate sign types, or a flag on existing types?
