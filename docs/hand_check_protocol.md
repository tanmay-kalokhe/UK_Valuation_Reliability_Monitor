# Hand-check protocol: which certificate belongs to the sale?

**Purpose:** create the ground truth used to measure the precision and recall of the SQL matching rules and of Splink (decision D-019). The labels must reflect what the addresses say, not what either method chose.

**The file:** `data/interim/hand_check/hand_check_sheet.csv`. It is created by `py -3.12 -m valuation_monitor.match_review sample`. It contains addresses, so it stays on this computer: do not email it, upload it, paste it into a chat tool or commit it. `.gitignore` already excludes it.

## What is on the sheet
- **Sale:** one row per sale (300 rows), showing the Land Registry address, postcode, date, property type, new-build flag and tenure.
- **Candidates:** `candidate_1` to `candidate_8` are properties at the same postcode that hold an energy certificate. Each shows the address on the property's most recent certificate, the EPC property type, the number of certificates and the years they were lodged.
- **`properties_at_postcode`:** how many properties at the postcode have a certificate. When it is larger than the number shown, only the eight closest addresses are listed.
- **Hidden information:** the sheet does not say which candidate the matching rules chose, or which group the sale was drawn from. Please do not look these up while labelling.

## How to label
Open the file in Excel. Fill in **`answer`** for every row:

| Answer | Meaning |
|---|---|
| `1` to `8` | That candidate is the **same dwelling** as the sale |
| `0` | None of the listed candidates is the same dwelling |
| `?` | You cannot decide from the information shown (explain in `notes`) |

Use **`notes`** for anything unusual, for example "house split into flats" or "two candidates look identical".

When you save, keep the **CSV** format (File → Save As → CSV UTF-8). Do not sort the rows or rename the columns. If Excel offers to convert values, choose not to convert.

## Rules for deciding "same dwelling"
1. **Same dwelling, not the same building.** Flat 3 and Flat 4 at the same address are different dwellings. A house number with no flat number is not the same as a flat in that house.
2. **Formatting does not matter.** Treat these as the same: capitalisation, punctuation, "Flat 3" vs "Apartment 3" vs "3", "Road" vs "Rd", and the order of the parts (for example "Flat 3, 24 Mill Lane" vs "24 Mill Lane, Flat 3").
3. **Extra locality words are allowed.** The certificate may add a hamlet, village or town, or omit the street, when the house name or number and the rest agree (common in Cornwall).
4. **Numbers must agree.** "24" and "24A" are different dwellings, as are "24" and "26". A range such as "24-26" matches only "24-26".
5. **House names.** Small spelling differences ("Rose Cottage" vs "Rosecottage", "The Old Barn" vs "Old Barn") are the same dwelling. Different names, even with similar words ("Rose Cottage" vs "Rose Barn"), are not.
6. **Property type is supporting evidence only.** Land Registry and the EPC sometimes describe the same home differently (for example a maisonette recorded as a house). Do not reject a candidate on type alone when the address clearly agrees. Note the disagreement instead.
7. **Two identical candidates.** If two candidates show the same address, the certificate data holds duplicate property identifiers. Answer with the lower candidate number and write "duplicate" in `notes`. Both count as correct when scoring.
8. **Certificate dates do not matter.** Judge only whether it is the same dwelling, even if every certificate was lodged after the sale. The rule "use the latest certificate before the sale" is applied separately.
9. **When unsure, use `?`.** Guessing would make the measurement look more certain than it is.

## Quality checks
- **Time:** expect about 30 to 60 seconds per row, so 3 to 5 hours in total. Two or three sittings work better than one.
- **Consistency:** after finishing, re-label 30 rows chosen at random without looking at your first answers (`py -3.12 -m valuation_monitor.match_review recheck` will draw them). The agreement rate is reported alongside the results as a measure of label reliability.
- **When you have finished:** tell Claude. The labels will be loaded and checked for blanks and invalid values before any scoring.

## How the labels are used
- **Weighting:** each sale was drawn from a group defined by the SQL outcome, and rare groups were over-sampled. Estimates are re-weighted by group size, so the over-sampling does not distort the overall figures.
- **Precision:** of the sales a method links, the weighted share linked to the property you chose.
- **Recall:** of the sales whose property appears among the candidates, the weighted share a method links correctly.
- **Uncertainty:** both figures are reported with bootstrap 95% confidence intervals. `?` answers are excluded and counted separately.
- **Limitation:** for postcodes with more than eight properties, the correct property could in principle fall outside the shortlist. The shortlist always includes every property the rules considered, then the closest addresses, so this should be rare. The number of `0` answers at such postcodes is reported.
