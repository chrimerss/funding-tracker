# Funding Tracker

Static dashboard of funding opportunities, deployed to GitHub Pages.

- Search, domain/keyword/status filters, sorting by deadline or amount
- Deadline status: open, closing soon (≤ 30 days), closed
- Calendar export (`deadlines.ics`, with a 2-week reminder)
- Summary charts: count by domain, deadlines per month

## Add an opportunity

Append an entry to [`data/opportunities.yaml`](data/opportunities.yaml) (field reference at the top of the file), then:

```bash
pip install -r requirements.txt
python scripts/build.py --check   # validate
python scripts/build.py           # build into _site/
python -m http.server -d _site    # preview at http://localhost:8000
```

Push to the default branch and the GitHub Action rebuilds and redeploys. It also rebuilds daily.

## One-time GitHub Pages setup

Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Layout

```
data/opportunities.yaml   source of truth
scripts/build.py          validate + build data.json and deadlines.ics
web/index.html            dashboard (vanilla JS, no dependencies)
.github/workflows/pages.yml
```
