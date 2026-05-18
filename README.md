# AI Music Traction Analysis

**DSA 210 – Introduction to Data Science**
**Student:** Pelin Umur – 35286

---

## Motivation

With the rapid rise of AI tools, producing music has become significantly easier. A growing number of new artists and songs are released on streaming platforms daily, and a considerable portion of these contain AI-generated content.

This project investigates whether artists who use AI-generated music at the start of their careers gain higher early-stage listens compared to artists who don't. Deezer flags albums containing AI-generated content, making it possible to identify and compare these two groups using real streaming data.

---


## Data Sources

### 1. Deezer (Web Scraping)
- **Method:** Selenium-based scraper targeting Deezer album pages
- **Data collected:** AI-generated content flag, album metadata, artist fan counts, genre, track count, release date
- **Filtering:** Albums collected via genre chart endpoints (`api.deezer.com/chart/{genre_id}/artists`) to avoid content-farm pollution; year-filtered at the API level to target recent releases

### 2. Last.fm API
- **Data collected:** Artist playcount, listener count, album playcount
- **Usage:** Computing playcount/listener ratios to assess traction and detect potential bot-like listening patterns

---

## Data Pipeline

```
Deezer scraper → raw CSV → Last.fm enrichment → merged dataset → analysis
```
### 1. Data Preparation
- One album per artist, most recent release prioritized
- Matched Deezer artists with Last.fm artist profiles
- Last.fm enrichment with fuzzy artist/album matching
- Removed invalid or incomplete observations
- Constructed playcount-to-listener ratios


### 2. Exploratory Data Analysis (EDA)

EDA focused on identifying structural differences between AI and Non-AI artists:
- Distribution comparisons
- Scatter plots of listeners vs playcounts
- Ratio histograms and boxplots
- Outlier analysis
- Class imbalance inspection

All generated figures are stored in the `figures/` directory.

---

### 3. Feature Engineering

Constructed analytical features including:
- Artist playcount-to-listener ratio
- Album playcount-to-listener ratio
- Deezer fan statistics
- Binary AI classification labels

---

## Dataset Overview

Final dataset size:

- **1585 total artists**
- **263 AI-flagged artists (16.6%)**
- **1322 Non-AI artists (83.4%)**

The dataset is therefore strongly imbalanced toward Non-AI artists.

---


## Hypothesis Testing

| Hypothesis | Description | Result |
|-----------|-------------|--------|
| **H1** | AI artists have a lower playcount/listener ratio than Non-AI artists | **Rejected** — Non-AI artists actually have significantly higher ratios |
| **H2** | AI artists have fewer Deezer fans than Non-AI artists | **Confirmed** |
| **H3** | AI artists have fewer Last.fm listeners than Non-AI artists | **Confirmed** |
| **H4** | The album playcount-to-listener ratio is lower for AI artists | **Mixed / Inconclusive** |

---


## Key Findings

1. **H1 rejected:** Non-AI artists have higher playcount/listener ratios, not lower. This suggests Non-AI artists attract more replays per unique listener.
2. **Classification is difficult:** The 87/13 class imbalance makes standard accuracy a misleading metric. Models default to predicting Non-AI for almost every case.
3. **AI artists cluster at low engagement:** The scatter plot shows AI-flagged artists are concentrated at very low listener and playcount values, consistent with being early-career or low-visibility artists.
4. **Bot signal is inconclusive:** Extremely high play/listener ratios that would indicate bot behavior exist in both groups as outliers.

---

## Limitations

- - Although the full dataset contains 263 AI-flagged artists, only 37 AI artists appeared in the final test set used for model evaluation, making it unstable.
- Last.fm matching is imperfect — some artists may be mismatched or missing
- Deezer's AI flag may not capture all AI-generated content
- Data scraped at a single point in time; traction evolves over time

## Future Work

- Address class imbalance with SMOTE oversampling
- Collect longitudinal data to track traction over time
- Add Spotify or Apple Music data for cross-platform comparison
- Use listener growth rate rather than absolute counts
- Explore neural network approaches with richer feature sets

---

## AI Assistance Disclosure

AI tools (Claude, ChatGPT) were used for web scraping, debugging code and adjusting the readme file. All hypothesis formulation, data collection decisions, and analysis were performed independently.
