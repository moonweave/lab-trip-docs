# Final Review

## What This Version Handles Well

- Collecting many trip documents in one central place
- Reducing manual sorting by traveler and category
- Detecting ambiguous shared documents instead of over-confidently assigning them
- Giving admins a review queue with confidence, evidence, and extracted text preview
- Creating Excel and ZIP packages for archiving
- Preserving existing document assignments when the roster is uploaded again

## Core Logic Review

The most important logic is the document analyzer. It now combines text, filename, traveler roster, aliases, and uploader name. Strong text matches can be auto-matched. Uploader-only matches are treated as candidates and remain in `needs_review`. If multiple strong traveler names are found, the document is not assigned automatically.

Document classification is still heuristic. This is intentional for the internal MVP because it is transparent and easy to tune with real lab documents. Each category stores matched keyword evidence so admins can understand why the system made a suggestion.

## Known Risks

- Image OCR is not enabled by default.
- Scanned PDFs with no embedded text remain in `needs_review`.
- Basic Auth is enough for lab MVP but not for public deployment.
- Korean text in generated PDFs depends on installed fonts.
- Some airline or conference documents have unusual layouts and need manual review.

## Recommended Next Real-Data Test

Use one past trip folder with 3 to 5 travelers and 30 to 50 documents. Measure:

- how many documents were categorized correctly
- how many were matched to the correct person
- how many were correctly left in `needs_review`
- which filenames or document types need custom keywords
- what exact Excel columns the institution requires
