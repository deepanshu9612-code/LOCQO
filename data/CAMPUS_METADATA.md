<!-- Generated during project kickoff. Sources: reference_docs (layout plan, labs list, logo, report) + krmangalam.edu.in scrape + tourmkr.com/F1Zr0N570h 360 tour. -->

# KRMU Campus Metadata

> **Source legend** — every entry is tagged so facts and guesses never blur:
> **[F]** = ground-truth layout plan / labs list (authoritative). **[S]** = scraped KRMU marketing pages (lower confidence; generic, no block/floor/room data). **[I]** = inference (clearly marked, not from any source).
> When **[F]** and **[S]** conflict, **[F]** wins. No room numbers are invented — only those in the ground-truth labs list appear.

---

## 1. Campus Overview

| Field | Value | Src |
|---|---|---|
| Name | K.R. Mangalam University (KRMU), Gurugram | F/S |
| Address | Sohna Road, Gurugram, Haryana – 122103 | S |
| Size / setting | 35-acre campus, Aravalli Hills | S |
| Main entrance | Main Gate at the **south**, on Sohna Road | F |
| Road orientation | **West** of gate = "towards Gurugram"; **East** = "towards Sohna" | F |
| Gate features | Security cabin, separate **Entry** and **Exit** lanes, flagpole, ATM beside the gate | F |
| University scale (marketing) | 12 Schools, 700+ faculty, 100+ teaching/research labs, 2 cafés per block | S |

**Rough north–south spine [F]:** Main Gate (south) → Block A → Canteen → Block B (W) / Block C (E) around a central quad → central Football Ground → driveway north → Block D. Hostels sit far **west**; bus/vehicle parking bays run along the far **east** edge.

---

## 2. Blocks & Buildings

| Building | Location (relative) | Contains | Floors (evidenced) | Notable rooms | Src |
|---|---|---|---|---|---|
| **Block A** | Immediately **north of Main Gate**; circular feature/fountain out front, stepped main entrance | **Library** (inside Block A), ground-floor labs | Ground (floor 0) confirmed; upper floors likely but unconfirmed | LAB 1 (A009), LAB 3 (A011), LAB 4 (A014); Library labs (LAB 10, 11, 17) | F |
| **Block B** | **West** of the central quad; long building parallel to Block C | Labs spread across floors 0–5 | Floors **0,1,2,4,5** evidenced → **≥6 levels** | see Labs table (B005, B102, B2xx, B402, B5xx) | F |
| **Block C** | **East** of the central quad; parallel to Block B. **Chinese Outlet** + **Nescafe Outlet** attached; **electricity substation** just east | Labs on floors 0,1,4 | Floors **0,1,4** evidenced → **≥5 levels** | LAB 8 (C015), LAB 12 (C102), LAB 13 (C404) | F |
| **Block D** | Set apart to the **north**, reached by a driveway; its own **football ground to the west**, small standalone structure to the **northeast** | Unknown | Unknown | none in labs list | F |
| **Canteen** | **Between Block A and Block B** | Dining | — | — | F |
| **Boys Hostel** (Vivekanand Hostel, male) | **Far west** of campus | 4-share rooms, gym, indoor games, mess, convenience store, warden office | Unknown | — | F (position) / S (name, amenities) |
| **Girls Hostel** (Gayatri Hostel, female) | **Far west** of campus | Same amenity set as Boys Hostel | Unknown | — | F (position) / S (name, amenities) |

> Block-A/B/C/D are the **only** confirmed academic block letters (from room codes + layout plan). Scraped pages call them "academic blocks" generically but never assign letters, floors, or rooms.

---

## 3. Schools / Departments

Ground-truth sources map **no** school to a block. All block guesses below are therefore **"unknown — needs survey"**; none is inferable from the data.

| # | School | Website slug | Block | Src |
|---|---|---|---|---|
| 1 | School of Engineering & Technology (SOET) | `school-of-engineering-and-technology` | unknown | S |
| 2 | School of Management & Commerce (SOMC) | `school-of-management-and-commerce` | unknown | S |
| 3 | School of Legal Studies (SOLS) | `school-of-legal-studies` | unknown | S |
| 4 | School of Medical & Allied Sciences (SMAS) | `school-of-medical-and-allied-sciences` | unknown | S |
| 5 | School of Physiotherapy & Rehabilitation Sciences | `school-of-physiotherapy-and-rehabilitation-sciences` | unknown | S |
| 6 | School of Liberal Arts (SOLA) | `school-of-liberal-arts` | unknown | S |
| 7 | School of Architecture & Design (SOAD) | `school-of-architecture-design` | unknown | S |
| 8 | School of Basic & Applied Sciences (SOBAS) | `school-of-basic-and-applied-sciences` | unknown | S |
| 9 | School of Emerging Media & Creator Economy | `school-of-emerging-media-and-creator-economy` | unknown | S |
| 10 | School of Hotel Management & Catering Technology | `school-of-hotel-management-and-catering-technology` | unknown | S |
| 11 | School of Education (SOED) | `school-of-education` | unknown | S |
| 12 | School of Agricultural Sciences (SOAS) | `school-of-agriculutural-sciences` *(slug misspelt "agriculutural" on the live site)* | unknown | S |
| 13 | **DATA GAP — 13th school** | not scraped | unknown | — |

> **Count discrepancy:** the task specifies **13** schools, but only **12** school pages were scraped and the KRMU pages themselves cite **"12 Schools."** The 13th is unresolved — see Data Gaps.

---

## 4. Labs (ground-truth labs list) **[F]**

Room-code scheme: **Block letter + floor digit + 2-digit room** (e.g. `B517` = Block B, floor 5, room 17).

| Lab ID | Room code | Block | Floor | Room |
|---|---|---|---|---|
| LAB 1 | A009 | A | 0 (Ground) | 09 |
| LAB 3 | A011 | A | 0 | 11 |
| LAB 4 | A014 | A | 0 | 14 |
| LAB 5 | B102 | B | 1 | 02 |
| LAB 6 | B402 | B | 4 | 02 |
| LAB 8 | C015 | C | 0 | 15 |
| LAB 9 | B005 | B | 0 | 05 |
| LAB 10 | A Library | A | — | Library (in Block A) |
| LAB 11 | A Library | A | — | Library (in Block A) |
| LAB 12 | C102 | C | 1 | 02 |
| LAB 13 | C404 | C | 4 | 04 |
| LAB 14 | B508 | B | 5 | 08 |
| LAB 15 | B202 | B | 2 | 02 |
| LAB 16 | B207 | B | 2 | 07 |
| LAB 17 | A Library | A | — | Library (in Block A) |
| LAB 19 | B504 | B | 5 | 04 |
| LAB 20 | B517 | B | 5 | 17 |
| LAB 21 | B205 | B | 2 | 05 |
| LAB 22 | B209 | B | 2 | 09 |

**Notes:** LAB 2, LAB 7, LAB 18 are **absent** from the source list (gaps, not typos). The labs list uses generic "LAB N" numbers — it does **not** name disciplines, so the scraped discipline labs (Physics, Chemistry, Robotics, Pharmacology, Training Kitchen, etc.) **cannot** be matched to these room codes with the current data.

---

## 5. Facilities & Amenities

| Facility | Location | Category | Src |
|---|---|---|---|
| Library | Inside **Block A**; online portal `library.krmangalam.edu.in` | library | F (block) / S (portal) |
| Canteen | Between Block A and Block B | eatery | F |
| Chinese Outlet | Attached to Block C | food kiosk | F |
| Nescafe Outlet | Attached to Block C | food kiosk | F |
| Cafés (2 per block) | One pair in each block | eatery | S |
| Training Restaurant | Unknown (Hotel Management school) | eatery | S |
| Hostel mess + convenience store | In hostel buildings (far west) | eatery/store | S |
| Central Football Ground | Large, central, **north of the quad** | ground | F |
| Block-D Football Ground | West of Block D (north campus) | ground | F |
| Basketball Ground | West of central football ground | ground | F |
| Cricket Ground | West of central football ground | ground | F |
| Two small courts | Near basketball/cricket (unnamed on plan) | ground | F |
| Tennis / Volleyball / Badminton / Pickleball courts | Outdoor, exact spots unknown | ground | S |
| Indoor games (table tennis, foosball, billiards, chess, carrom) | In hostel / sports area | facility | S |
| Modern gym | Hostel area | amenity | S |
| Visitor Parking | **West** of Main Gate | parking | F |
| Student Parking | **East** of Main Gate | parking | F |
| Bus/vehicle parking bays | Far **east** edge | parking | F |
| ATM | Beside Main Gate | amenity | F |
| Electricity substation | East of Block C | utility | F |
| Flagpole | At Main Gate | landmark | F |
| Boys Hostel (Vivekanand) / Girls Hostel (Gayatri) | Far west | hostel | F/S |
| Warden Office | In hostel block | office | S |
| Central Instrumentation Facility (CIF) | Block unknown | lab | S |
| Moot Court | Block unknown (Legal Studies) | facility | S |
| Career Development Centre, Registrar Office, Finance Dept | Block unknown | office | S |
| ~14 student clubs/societies | **Organizations, not physical rooms** — excluded from map pins | — | S |

---

## 6. Candidate Destinations for the App

Flat, navigable points. `block`/`floor` filled only where a source gives them; `—` = not applicable/unknown. Lab pins carry their room code.

| id | Display name | Category | Block | Floor | Src |
|---|---|---|---|---|---|
| `main-gate` | Main Gate | gate | — | — | F |
| `atm-main-gate` | ATM (Main Gate) | amenity | — | — | F |
| `visitor-parking` | Visitor Parking | parking | — | — | F |
| `student-parking` | Student Parking | parking | — | — | F |
| `bus-parking` | Bus / Vehicle Parking Bays | parking | — | — | F |
| `block-a` | Block A | block | A | — | F |
| `block-b` | Block B | block | B | — | F |
| `block-c` | Block C | block | C | — | F |
| `block-d` | Block D | block | D | — | F |
| `library` | Library | library | A | — | F |
| `canteen` | Canteen | eatery | — | — | F |
| `chinese-outlet` | Chinese Outlet | eatery | C (attached) | — | F |
| `nescafe-outlet` | Nescafe Outlet | eatery | C (attached) | — | F |
| `football-ground-central` | Football Ground (Central) | ground | — | — | F |
| `football-ground-d` | Football Ground (Block D) | ground | — | — | F |
| `basketball-ground` | Basketball Ground | ground | — | — | F |
| `cricket-ground` | Cricket Ground | ground | — | — | F |
| `boys-hostel` | Boys Hostel (Vivekanand) | hostel | — | — | F/S |
| `girls-hostel` | Girls Hostel (Gayatri) | hostel | — | — | F/S |
| `electricity-substation` | Electricity Substation | utility | — | — | F |
| `lab-1` | Lab 1 (A009) | lab | A | 0 | F |
| `lab-3` | Lab 3 (A011) | lab | A | 0 | F |
| `lab-4` | Lab 4 (A014) | lab | A | 0 | F |
| `lab-5` | Lab 5 (B102) | lab | B | 1 | F |
| `lab-6` | Lab 6 (B402) | lab | B | 4 | F |
| `lab-8` | Lab 8 (C015) | lab | C | 0 | F |
| `lab-9` | Lab 9 (B005) | lab | B | 0 | F |
| `lab-10` | Lab 10 (Library) | lab | A | — | F |
| `lab-11` | Lab 11 (Library) | lab | A | — | F |
| `lab-12` | Lab 12 (C102) | lab | C | 1 | F |
| `lab-13` | Lab 13 (C404) | lab | C | 4 | F |
| `lab-14` | Lab 14 (B508) | lab | B | 5 | F |
| `lab-15` | Lab 15 (B202) | lab | B | 2 | F |
| `lab-16` | Lab 16 (B207) | lab | B | 2 | F |
| `lab-17` | Lab 17 (Library) | lab | A | — | F |
| `lab-19` | Lab 19 (B504) | lab | B | 5 | F |
| `lab-20` | Lab 20 (B517) | lab | B | 5 | F |
| `lab-21` | Lab 21 (B205) | lab | B | 2 | F |
| `lab-22` | Lab 22 (B209) | lab | B | 2 | F |

---

## 7. Data Gaps & Assumptions (needs on-site survey)

1. **School → block mapping:** No source places any of the 12 (or 13) schools in a specific block/floor. Entirely unsurveyed.
2. **13th school identity:** Task expects 13 schools; only 12 are in the data, and KRMU's own pages say "12 Schools." The 13th must be confirmed on-site — **not invented here**.
3. **Discipline labs vs room codes:** Scraped pages name discipline labs (Physics, Robotics, Pharmacology, Training Kitchen, etc.) with **no** room codes; the ground-truth list has room codes but only generic "LAB N" labels. Mapping the two requires a survey.
4. **Missing labs:** LAB 2, 7, 18 are absent from the ground-truth list — unknown whether decommissioned, renumbered, or simply omitted.
5. **Floor counts:** Only floors that appear in room codes are confirmed (A: floor 0; B: 0–5; C: 0,1,4). Total heights, and Block A's upper floors, are unverified. **[I]** B is likely ≥6 storeys and C ≥5, but only from the highest room code seen.
6. **Block D & north campus:** Contents of Block D and the standalone NE structure are unknown.
7. **Intra-building navigation:** No corridors, staircases, lifts, entrances, or room adjacencies are documented — only exterior block positions. Turn-by-turn indoor routing is not yet possible.
8. **Precise coordinates:** The layout plan gives relative positions (N/S/E/W), not lat/long or a scaled grid. A geo-referenced map or measured plan is needed for a real routing graph.
9. **Exact placement of shared amenities:** CIF, moot court, admin offices (Registrar, Finance, Career Development), Training Restaurant, individual courts, gym, and mess have no confirmed block/floor.
10. **Library sub-page** (`library.krmangalam.edu.in`) is a JS single-page app that returned no content — internal library sections/floors remain unscraped.


---

## 8. Virtual Tour Indoor POI Catalog (175 scenes) **[T]**

Source: official 360° tour `https://tourmkr.com/F1Zr0N570h` (GoThru/TourMaker). This is the richest indoor inventory we have — every scene is a real, photographed place. **Caveat:** scenes carry NO floor/room/coordinate data and the tour's category names do not map to Blocks A/B/C/D. Treat these as candidate destinations/POIs, not as located points, until an on-site survey assigns each a block+floor.

Raw machine-readable version: [`tour_scenes.json`](tour_scenes.json).


**Top Level / Entry** (14) — Aerial View, Kr Mangalam University, Entrance Gate 1, Entrance Gate 2, Campus View 1, Campus View 2, Campus Pathway, Student Security Point, Sunken Garden, University Lobby, University Reception, Admission Department, KEIC Foundation, IKS Gallery -Bhartiya Gyan Vithika

**University Facilities** (7) — Conference Room, Vice Chancellor Office, Registrar Office, Design Thinking, Museum / Virasat, Girls Comman Room, Boy's Comman Room

**Central Library** (8) — Library Corridor, Digital Library, Reading Section, General Section, Research Section, Reference Room, Law Books Section, Perodical Section

**School Of Engineering** (14) — Robotics & Automation, Center of AI Excellence, SOET Conference Room, iOS Lab, IBM Lab, Basic Electrical & Electronics Engineering lab, Class Room, Phonex Drone lab, Eng. Workshop Lab, Computer Lab, Computer Lab 2, Computer Lab 3, Computer Lab 4, Machine room

**School Of Architecture** (11) — Corridor View 1, Corridor View 2, Exhibition room, Fine Arts Studio, Interior Design Studio, Architecture Studio, Corridor(Fashion Studio), Garments Construction Lab, Museum Fashion Design, Fashion Design Studio, Pattern Making Lab

**School Of Management** (2) — Simulation Lab, Class Room

**School Of Legal Studies** (3) — Moot Court Room, Legal Aid Center, Classroom

**School Of Medical Science** (19) — Corridor Section, Physiology Lab, Pharmaceutics Lab 1, Pharmaceutics Lab 2, Pharmaceutics Lab 3, Pharma Chemistry Lab 1, Pharma Chemistry Lab 2, Pharmaceutical Chemistry lab 3, Pharma Microbiology Lab, Social Pharmacy, Pharmacology Lab, Pharmacognosy lab, Pharmaceutics Lab 1, Pharmaceutics lab 2, Pharmacology Lab 1, Pharmacology Lab 2, Musuem Room, Animal House, Class Room

**School Of Basic Science** (6) — Forensic Science lab, Chemistry Lab 1, Chemistry Lab 2, Physics Lab 1, Physics Lab 2, CIF Lab

**School Of Hotel Managment** (7) — Conference Room, Guest Mock Room, House Keeping Room, Reception, Restaurant, Kitchen, Class Room

**School Of Journalism** (5) — Corridor (Mass Comm.), TV Studio, Production Control Room (PCR), Radio/Podcast room, Digital Class Room

**School Of Humanities** (5) — Corridor Area, Corrdor Area, Conference Room, Psychology Lab, Class Room

**School Of Education** (4) — Corridor View, Curriculum Lab / Resource Center, Multipurpose Hall, Class Room

**School Of Agriculture** (17) — Entomology Lab, Horticulture Lab, Nursery, Poly House, Shed Net House, Mushroom Unit, Organic Vegetables, Green Net House, Crop Cafeteria, Agronomy & Soil Lab, Soil science lab, Post Harvest Processing lab, Baby Plant Area, Organic Broccoli, Horticulture Farm, Art Gallary, Class Room

**School Of Physiotherapy** (7) — Physiotherapy OPD, Electrotherapy Lab, Anatomy Lab, Exercise Therapy Lab, Functional Diagnostic Lab, Biomechanics & Kinesiology Lab, Exercise Tolerance and Fitness Lab

**Career Development Centre** (6) — Seminar Hall -Pre Placemrnt Talk, Technical Training Facilities, Department of Student Welfare, Counseling Room, CDC Office, International Relations Office

**Outdoor Sports Facilities** (6) — Cricket Net Practice, Football & Athletics, Basketball Court, Volleyball Court, Tennis Court, Cricket Ground

**Indoor Sports Facilities** (7) — Corridor, Pool Table, T.T. Room, Dance Room, Foosball Room, Chess Room, Carrom Room

**Hostel** (12) — Pathway, Front View, Reception, Badminton Court, Gym Area, Futsal Court, Utility Room, Boy's Room, Girl's Room, Laundry Facility, Mess, Medical Room

**Caféteria** (3) — Canteen, Café coffee day, Sandwich Junction

**Parking** (12) — Car Parking, Bike Parking, Areial View, Sunken Garden, University Reception, Central Library, Admission Department, KEIC Foundation, IKS Gallery, Conference Room, Seminar Hall -Pre Placemrnt Talk, Medical Room


---

## 9. Source Files

| File | What it is |
|---|---|
| `reference_docs/college layout.pdf` | Official site plan (authoritative outdoor base map) |
| `data/college_layout.png` | Rendered PNG of the site plan |
| `reference_docs/labs list.jpeg` | 19 labs → room codes (Block+Floor+Room) |
| `reference_docs/logo.jpeg` | LOCQO brand logo |
| `reference_docs/report.pdf` | Original student project brief |
| `data/tour_scenes.json` | 175 tour scenes grouped by category |
| `data/CAMPUS_METADATA.md` | This consolidated metadata document |
