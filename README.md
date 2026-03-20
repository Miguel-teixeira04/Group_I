# Group_I
ADPRO Group Project

## Team

Guilherme Morgado (56857@novasbe.pt)
Isaac Carvalho    (57045@novasbe.pt)
Matilde Ferreira  (56599@novasbe.pt)
Miguel Teixeira   (56529@novasbe.pt)

---

## Project Structure

```text
Group_I/
├── app/                   # Main application modules
│   ├── data_loader.py     # Downloads datasets
│   ├── data_manager.py    # Manages and merges data
│   ├── image_loader.py    # Fetches satellite images
│   ├── merger.py          # Merges geodata
│   ├── ollama_pipeline.py # AI analysis pipeline
│   └── storage.py         # Cache and persistence
├── database/
│   └── images.csv         # History of AI analysis runs
├── downloads/             # Downloaded datasets
├── notebooks/             # Prototyping notebooks
├── pages/                 # Streamlit pages
├── tests/                 # pytest test suite
├── models.yaml            # AI model configuration
├── main.py                # App entry point
└── requirements.txt
```
---

## About the Project

This tool analyses environmental data from [Our World in Data](https://ourworldindata.org) and combines it with AI-powered satellite image analysis to assess environmental risk across the globe.

It addresses the following UN Sustainable Development Goals (SDGs):

- **SDG 15 — Life on Land**: Monitoring deforestation, land degradation, and protected areas
- **SDG 13 — Climate Action**: Tracking annual forest area changes as a climate indicator

---

## How to Run the App

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/Group_X.git
cd Group_X
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Launch the Streamlit app

```bash
run main.py
```

On first launch, the app will automatically download all required datasets into the `downloads/` directory. This may take a moment depending on your internet connection.

---

## Examples

### Example 1 


### Example 2 


### Example 3

---

## Running Tests

```bash
pytest
```