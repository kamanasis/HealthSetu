# HealthSetu — Design System & Guidelines

## 1. Brand Identity

* **Product Name:** HealthSetu
* **Tagline:** Your health, always connected.
* **Mission:** Bridging patients, doctors, and hospitals into one secure, continuous care platform.
* **Tone:** Calm. Trustworthy. Accessible. Human. Professional without being clinical.

---

## 2. Design Stance

* **Aesthetic:** Minimalist — generous whitespace, clean type hierarchy, restrained use of color.
* **Inspiration:** Apple Health, Aesop product pages — one primary element per section, tight typography, light surfaces.
* **Commitment:** Every screen should feel airy and safe, not busy. Medical information should never feel overwhelming or cluttered.

---

## 3. Color Palette

### Primary Colors
| Token | Hex | Usage |
| :--- | :--- | :--- |
| `--background` | `#FAF8F3` | Page background (warm cream) |
| `--foreground` | `#1C2B3A` | Primary text, headings |
| `--primary` | `#4A90C4` | Sky blue — primary actions, links, highlights |
| `--primary-foreground` | `#FFFFFF` | Text on primary blue |
| `--accent` | `#3D8B6E` | Sage green — secondary actions, success states |
| `--accent-foreground` | `#FFFFFF` | Text on sage green |

### Surface Colors
| Token | Hex | Usage |
| :--- | :--- | :--- |
| `--card` | `#FFFFFF` | Card and panel backgrounds |
| `--card-foreground` | `#1C2B3A` | Card text |
| `--secondary` | `#EBF5EC` | Light mint — green-tinted surfaces |
| `--secondary-foreground` | `#2D5A40` | Text on mint surfaces |
| `--muted` | `#F0EDE7` | Subdued surfaces, tags, chip backgrounds |
| `--muted-foreground` | `#6B7A8D` | Labels, captions, secondary text |

### Border & Focus
| Token | Hex | Usage |
| :--- | :--- | :--- |
| `--border` | `#DDD9D1` | Hairline borders, dividers |
| `--ring` | `#4A90C4` | Focus rings on interactive elements |

### Semantic / Role Colors
| Role | Hex | Context |
| :--- | :--- | :--- |
| **Patient blue** | `#4A90C4` / `#EBF4FB` | Patient-facing elements |
| **Doctor green** | `#3D8B6E` / `#EBF5EC` | Doctor-facing elements |
| **Hospital purple** | `#7B5EA7` / `#F5F0FC` | Hospital-facing elements |
| **Emergency orange** | `#E07B39` / `#FEF3E8` | Emergency, alerts, warnings |
| **Warning rose** | `#D94F7A` / `#FDEEF4` | Critical medication or safety alerts |
| **Neutral slate** | `#6B7A8D` | Secondary text, inactive states |

### Color Usage Rules
* Blue is the primary interactive color. Use it for primary buttons, active states, and patient-role indicators.
* Green is the secondary action and success color. Use it for approval states, doctor-role indicators, and positive outcomes.
* Orange is reserved for emergency-related UI and medication safety warnings.
* Purple is hospital-specific only.
* Never use more than two accent colors in a single section.
* Background tints (e.g. `#EBF4FB`, `#EBF5EC`) are preferred over solid fills for badges and pill tags.

---

## 4. Typography

### Font Families
| Role | Family | Source |
| :--- | :--- | :--- |
| **Display / Headings** | DM Serif Display | Google Fonts |
| **Body / UI** | Nunito | Google Fonts |

### Import (Vite / CSS)
```css
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Nunito:wght@300;400;500;600;700;800&display=swap');
```

### Type Scale
| Element | Family | Size | Weight | Color |
| :--- | :--- | :--- | :--- | :--- |
| **H1 — Hero** | DM Serif Display | 56–64px | 400 (italic variant available) | `#1C2B3A` |
| **H2 — Section** | DM Serif Display | 36–40px | 400 | `#1C2B3A` |
| **H3 — Card** | DM Serif Display | 22–26px | 400 | `#1C2B3A` |
| **Body large** | Nunito | 18px | 400 | `#6B7A8D` |
| **Body default** | Nunito | 14–16px | 400–500 | `#1C2B3A` / `#6B7A8D` |
| **Label / caption** | Nunito | 12px | 600–700 | `#6B7A8D` |
| **Overline / tag** | Nunito | 11–12px | 700 | varies |
| **Button** | Nunito | 14px | 600–700 | varies |

### Typography Rules
* H1, H2, H3 always use DM Serif Display. All other text uses Nunito.
* Italic variant of DM Serif Display can be used for emphasis within headings (e.g. *always connected.*).
* Body copy line-height: 1.65–1.75 for readability.
* Heading line-height: 1.15–1.25.
* Never use italic body copy for clinical information — reserve it for decorative heading emphasis only.
* Uppercase tracking is allowed only for small overline labels (e.g. section tags, table column headers).

---

## 5. Spacing System

HealthSetu uses Tailwind's default spacing scale. Key reference points:

| Token | Value | Common usage |
| :--- | :--- | :--- |
| `1` | 4px | Fine gaps, icon margins |
| `2` | 8px | Tight internal padding |
| `3` | 12px | Component internal spacing |
| `4` | 16px | Default padding unit |
| `5` | 20px | Card padding |
| `6` | 24px | Section internal padding |
| `8` | 32px | Component separation |
| `10` | 40px | Section vertical spacing |
| `14` | 56px | Large section gaps |
| `20` | 80px | Full section vertical padding |
| `24` | 96px | Hero / CTA sections |

**Rule:** Be generous. When in doubt, add more whitespace rather than less. Dense medical information must breathe.

---

## 6. Border Radius

| Token | Value | Usage |
| :--- | :--- | :--- |
| `--radius` | 0.75rem (12px) | Default cards, panels |
| `rounded-lg` | 8px | Small chips, inputs |
| `rounded-xl` | 12px | Buttons, tags, mini cards |
| `rounded-2xl` | 16px | Cards, modals |
| `rounded-3xl` | 24px | Hero card, large containers |
| `rounded-full` | 9999px | Badges, avatar circles, pill tags |

---

## 7. Elevation & Shadow

| Level | Tailwind | Usage |
| :--- | :--- | :--- |
| **None** | — | Default flat cards |
| **Low** | `shadow-sm` | Cards in lists, subtle lift |
| **Medium** | `shadow-md` | Hovered cards, dropdowns |
| **High** | `shadow-xl` | Hero card, modals, floating panels |

* Shadows should use box-shadow defaults. Avoid colored shadows.
* Backdrop blur (`backdrop-blur-md`) is used on the fixed navigation bar.

---

## 8. Component Patterns

### Button
* **Primary**: `bg-[#4A90C4] text-white font-600 text-sm px-6 py-3 rounded-xl`
  * *Hover*: `bg-[#3A7DB0] transition-colors duration-200 shadow-sm`
* **Secondary / Outline**: `border border-[#DDD9D1] bg-white text-[#1C2B3A] font-600 text-sm px-6 py-3 rounded-xl`
  * *Hover*: `border-[#4A90C4]`
* **Emergency / Orange**: `bg-[#E07B39] text-white font-600 text-sm px-6 py-3 rounded-xl`
  * *Hover*: `bg-[#C96A28]`
* **Ghost**: `text-[#4A90C4] font-600 text-sm px-4 py-2 rounded-lg`
  * *Hover*: `bg-[#EBF4FB]`

### Card
* `bg-white rounded-2xl border border-[#DDD9D1] p-6`
* *Hover*: `shadow-md border-transparent -translate-y-0.5 transition-all duration-200`

### Badge / Pill Tag
* `inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-700`
* **Role-specific tints**:
  * Patient: `bg-[#EBF4FB] text-[#2B5F8A]`
  * Doctor: `bg-[#EBF5EC] text-[#2D5A40]`
  * Hospital: `bg-[#F5F0FC] text-[#5B3D8A]`
  * Warning: `bg-[#FEF3E8] text-[#A05520]`
  * Success: `bg-[#EBF5EC] text-[#3D8B6E]`
  * Danger: `bg-[#FDEEF4] text-[#D94F7A]`

### Status Indicator
Live status dots use a filled circle preceding the label:
```html
<span class="w-1.5 h-1.5 rounded-full bg-[#3D8B6E]" />
```
* **Active / Current**: `bg-[#3D8B6E]`
* **Warning / Stale**: `bg-[#C9A0A0]`
* **Offline**: `bg-[#DDD9D1]`

### Input / Search Field
* `bg-[#F0EDE7] rounded-xl px-3 py-2.5 text-sm`
* *Placeholder*: `text-[#6B7A8D]`
* *Focus*: `ring-1 ring-[#4A90C4] outline-none`

### Navigation Bar
Fixed. Height 64px. Background `#FAF8F3` at 90% opacity with `backdrop-blur-md`. Bottom border `border-[#DDD9D1]`. Z-index 50.

### Icon Style
All icons use SVG stroke icons at `strokeWidth={1.8}`, `strokeLinecap="round"`, `strokeLinejoin="round"`. No filled icons unless indicating a required state. Default icon sizes:
* 15px (inline)
* 19px (feature card)
* 22px (role card)
* 24px (CTA)

---

## 9. Role-Based Color System

Each user role has a consistent visual identity applied across cards, badges, buttons, and accents:

| Role | Primary | Background Tint | Text on Tint |
| :--- | :--- | :--- | :--- |
| **Patient** | `#4A90C4` | `#EBF4FB` | `#2B5F8A` |
| **Doctor** | `#3D8B6E` | `#EBF5EC` | `#2D5A40` |
| **Hospital** | `#7B5EA7` | `#F5F0FC` | `#5B3D8A` |
| **Emergency** | `#E07B39` | `#FEF3E8` | `#A05520` |

**Rule:** When an element is role-specific (a button, a card heading, a status tag), apply that role's color. Never mix role colors within a single card or widget unless displaying a cross-role interaction.

---

## 10. Data Trust Indicators

HealthSetu surfaces the provenance of all data. Use these visual patterns consistently:

| Data State | Visual Pattern |
| :--- | :--- |
| **AI-generated** | `bg-white/60` pill tag reading `"AI-generated · Review before use"` |
| **Patient-verified** | Green checkmark badge `text-[#3D8B6E]` |
| **Clinically recorded** | Doctor icon + institution label |
| **Raw / unverified** | Orange border or `bg-[#FEF3E8]` background |
| **Current (fresh)** | Green dot + `"Current"` label |
| **Stale** | Muted red dot + `"Stale"` label |
| **Unknown** | `bg-[#F0EDE7]` + `"Unknown"` label |

*Never display AI-generated clinical data without a visible provenance label.*

---

## 11. Layout Principles

### Grid System
* Page max-width: `max-w-6xl` (1152px) with `px-6` gutters.
* **Two-column sections**: `grid lg:grid-cols-2 gap-16` — typically content on left, interactive widget on right.
* **Three-column grids**: `grid lg:grid-cols-3 gap-6` — used for role cards and feature grids.
* **Feature cards**: `grid sm:grid-cols-2 lg:grid-cols-3 gap-5`.

### Section Rhythm
Every section follows this vertical rhythm:
* `py-20` for content sections
* `py-24` for CTA / hero sections
* Section dividers use `border-t border-[#DDD9D1]` or background color change (`bg-white` alternating with `#FAF8F3`).

### Asymmetry
Prefer intentional asymmetric compositions. The hero places a rich interactive widget on the right, not a static illustration. Two-column sections should feel like the content and the widget have different visual weights by design.

---

## 12. Imagery

* Photos sourced from Unsplash. Always use descriptive alt text. Set a background color on image containers so layout holds during load.
* Format: `https://images.unsplash.com/photo-{id}?w={width}&h={height}&fit=crop&auto=format`
* **Preferred image tonal treatment:** Images used in this platform should feel warm, human, and documentary — not stock-photo sterile. Prefer candid clinical environments over posed generic health imagery.

---

## 13. Motion & Transitions

All transitions use `duration-200` for micro-interactions and `duration-300` for card-level hover effects:

| Interaction | Effect |
| :--- | :--- |
| **Button hover** | `transition-colors duration-200` |
| **Card hover** | `hover:shadow-md hover:-translate-y-0.5 transition-all duration-300` |
| **Icon hover** | `group-hover:scale-110 transition-transform duration-300` |
| **Nav link hover** | `transition-colors duration-200` |

*No animated entrance effects (scroll-triggered animations) in the MVP. Keep motion conservative for a healthcare context.*

---

## 14. Accessibility

* Body text minimum contrast: 4.5:1 against background (`#1C2B3A` on `#FAF8F3` ≈ 11:1 ✓)
* Secondary text (`#6B7A8D` on `#FFFFFF` ≈ 4.6:1 ✓)
* Interactive elements must signal state with more than color alone (icon + label, not color alone).
* Focus rings use `ring-1 ring-[#4A90C4]` — visible on all surfaces.
* All icons include adjacent text labels or `aria-label` attributes.
* Clinical information is never conveyed by color alone.

---

## 15. Page Structure Reference

```html
<Nav />             <!-- Fixed, z-50, 64px height -->
<Hero />            <!-- pt-32 pb-20, two-column: copy + dashboard widget -->
<TrustStrip />      <!-- bg-[#EBF4FB] horizontal badge row -->
<RoleSection />     <!-- bg-white, three role cards -->
<HowItWorks />      <!-- two-column: 5-step journey + timeline card -->
<FeaturesGrid />    <!-- bg-white, 3-col, 9 capability cards -->
<EmergencySection/> <!-- two-column: copy + hospital search UI -->
<CTA />             <!-- centered gradient panel -->
<Footer />          <!-- bg-white, 4-col grid -->
```

---

## 16. Writing Style

* **Headings:** Sentence case. Short, declarative. No full stops.
* **Body copy:** Plain English. No unnecessary jargon. Max 2 sentences per feature description.
* **Button labels:** Action verbs. "Create Patient Account", "Find Hospitals Near Me", not "Submit" or "Click here".
* **Badge labels:** Title case. Short. "AI-generated", "Access Requested", "Current", "Stale".
* **Error and warning messages:** Factual, specific, non-alarming. "Metformin + Ibuprofen interaction noted" — not "DANGEROUS DRUG INTERACTION".
* **Placeholder data:** Always use realistic Indian names, hospital names, and clinical terminology. No lorem ipsum. No "John Doe".
* **AI output labels:** Always mark AI-generated content visibly. Never present AI conclusions as verified clinical facts.

---

## 17. Non-Negotiable Design Rules

1. Never display AI-derived clinical data without a provenance label.
2. Never use color as the sole differentiator for a critical state (allergy, emergency, stale data).
3. Availability data always shows a freshness indicator (`Current` / `Stale` / `Unknown`).
4. Role color identity (patient blue / doctor green / hospital purple) must remain consistent across every screen.
5. Emergency-related UI always uses the orange semantic color, never blue or green.
6. Medical terminology must not be altered in translated or simplified copy.
7. The trust hierarchy (`Raw` → `Extracted` → `Patient Verified` → `Clinically Recorded` → `AI Analyzed`) must be visually distinguishable at all times.
