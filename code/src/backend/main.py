import requests
import os
import json
import csv
import re
import pandas as pd
import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv
from transformers import pipeline

load_dotenv(find_dotenv())

GOOGLE_GEMINI_API = os.getenv("GOOGLE_GEMINI_API")
OPEN_CORPORATE_API = os.getenv("OPEN_CORPORATE_API")
GOOGLE_NEWS_API = os.getenv("GOOGLE_NEWS_API")

genai.configure(api_key=GOOGLE_GEMINI_API)

OFAC_SANCTIONS = pd.read_csv(os.path.join("sanction_list", "ofac_sanctions.csv"), usecols=[1], names=["Entity"], skiprows=1)
EU_SANCTIONS = pd.read_csv(os.path.join("sanction_list", "eu_sanctions.csv"), usecols=["NameAlias_WholeName"])
ICIJ_LEAKS = pd.read_csv(os.path.join("sanction_list", "icij_leaks.csv"), usecols=["name", "sourceID"])


GOOGLE_NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

# Risk scoring weights
WEIGHTS = {
    "sanctions": 50,
    "financial_risk": 30,
    "country_risk": 20,
    "adverse_media": 25,
    "shareholder_sanctions":25,
    "shareholder_negative_news":15
}

# Entity cache to avoid redundant API calls
ENTITY_CACHE = {}

# Load transaction data
def load_data(file_path):
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

# Get company info from OpenCorporateAPI
def get_info(company_name):
    url = f"https://api.opencorporates.com/v0.4/companies/search?q={company_name}&api_token={OPEN_CORPORATE_API}"
    response = requests.get(url).json()

def get_cik_from_sec(company_name):
    search_url = "https://www.sec.gov/cgi-bin/cik_lookup"  # SEC CIK Lookup endpoint
    headers = {
        "User-Agent": "joelvijo02@gmail.com"
    }

    # Send a POST request with the company name
    response = requests.post(search_url, headers=headers, data={"company": company_name})

    if response.status_code != 200:
        print(f"⚠️ Failed to fetch data from SEC. Status Code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Locate the CIK in the response page
    cik_element = soup.find("a", href=True, text=True)
    if cik_element:
        cik = cik_element.text.strip()
        return cik.zfill(10)  # Convert to 10-digit format

    print("⚠️ No CIK found. Try a different company name.")
    return None

def get_latest_filings(cik):
    base_url = "https://www.sec.gov"
    search_url = f"{base_url}/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=SC%2013G"
    HEADERS = {"User-Agent": "joelvijo02@gmail.com"}
    response = requests.get(search_url, headers=HEADERS)
    if response.status_code != 200:
        print("❌ Failed to fetch SEC filings")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    filings = soup.find_all("a", href=True)
    sc_13g_links = [base_url + f["href"] for f in filings if "Archives" in f["href"]]
    if(len(sc_13g_links)==0):
        return None
    return sc_13g_links[0]  # Return top N filings

def extract_group_members(company_name):
    cik = get_cik_from_sec(company_name)
    filing_url = get_latest_filings(cik)
    if(filing_url is None):
        return []
    HEADERS = {"User-Agent": "joelvijo02@gmail.com"}
    response = requests.get(filing_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    print(f"\n📄 Processing Filing: {filing_url}")

    # Find the "Group Members" section
    response = requests.get(filing_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    txt_link = None
    for link in soup.find_all("a", href=True):
        if link["href"].endswith(".txt"):  # Find the .txt file
            txt_link = "https://www.sec.gov" + link["href"]
            break

    if not txt_link:
        print("⚠️ No full submission text file found.")
        exit()

    print(f"✅ Found full text file: {txt_link}")
    response = requests.get(txt_link, headers=HEADERS)
    submission_text = response.text
    members = re.findall(r"GROUP MEMBERS:\s+(.*)", submission_text)
    shareholders_list = [m.strip() for m in members[:5]]
    for i, shareholder in enumerate(shareholders_list, start=1):
        print(f"{i}. {shareholder}")
    return shareholders_list

# Check if company is on any sanctions list
def check_sanctions(company_name):
    if OFAC_SANCTIONS[OFAC_SANCTIONS["Entity"].str.contains(company_name, case=False, na=False)].any().any():
        return "OFAC"
    if EU_SANCTIONS[EU_SANCTIONS["NameAlias_WholeName"].str.contains(company_name, case=False, na=False)].any().any():
        return "EU"
    match = ICIJ_LEAKS[ICIJ_LEAKS["name"].str.contains(company_name, case=False, na=False)]
    if not match.empty:
        return f"Panama Papers ({match.iloc[0]['sourceID']})"
    return None

# Fetch adverse media sentiment using Google News API
def fetch_adverse_media(company_name, n):
    negative_news=[]
    confidence_scores=[]
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    sentiment_pipeline = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
    GOOGLE_NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
    response = requests.get(GOOGLE_NEWS_API_URL, params={"q": company_name, "apiKey": GOOGLE_NEWS_API})
    if response.status_code != 200:
        return None, None
    articles = response.json().get("articles", [])
    if not articles:
        return None, None
    headlines = [summarizer(article["content"], max_length=50, min_length=10, do_sample=False) for article in articles[:n] if article["content"]]
    for h in headlines:
        sentiment = sentiment_pipeline(h[0]['summary_text'])
        if(sentiment[0]['label']=='1 star' or sentiment[0]['label']=='2 stars'):
            negative_news.append(h[0]['summary_text'])
            confidence_scores.append(sentiment[0]['score'])

    return negative_news, confidence_scores

# Compute risk score
def compute_risk_score(company_name, country, amount, shareholders):
    if company_name in ENTITY_CACHE:
        return ENTITY_CACHE[company_name]
    
    score = 0
    remarks = []

    # Sanctions check
    sanction_list = check_sanctions(company_name)
    if sanction_list:
        score += WEIGHTS["sanctions"]
        remarks.append(f"Found in {sanction_list}")
    
    # Adverse media sentiment
    sentiment, keyword = fetch_adverse_media(company_name)
    if sentiment is not None and sentiment < 0:
        score += WEIGHTS["adverse_media"]
        remarks.append(f"Negative news detected: {keyword}")
    
    ENTITY_CACHE[company_name] = (score, "; ".join(remarks), sanction_list, sentiment, keyword)
    return ENTITY_CACHE[company_name]

# Main function to process transactions
def process_transactions(data):
    # data = load_data(df)
    if data is None:
        return

    results = []
    for _, row in data.iterrows():
        supporting_evidence = []
        transaction_id = row["Transaction ID"]
        company1, company2 = row["Payer Name"], row["Receiver Name"]
        company1_sanction = check_sanctions(company1)
        if(company1_sanction):
            supporting_evidence.append(company1_sanction)
        company2_sanction = check_sanctions(company2)
        if(company2_sanction):
            supporting_evidence.append(company2_sanction)
        amount, country_1, country_2 = row["Amount"], row["Payer Country"], row["Receiver Country"]
        transaction_details = row["Transaction Details"]
        remarks = row["Remarks"]
        company_type_1 = get_info(company1)
        company_type_2 = get_info(company2)
        if(company_type_1 or company_type_2):
            supporting_evidence.append("OpenCorporate")
        shareholders_1 = extract_group_members(company1)
        shareholders_2 = extract_group_members(company2)
        if(shareholders_1 or shareholders_2):
            supporting_evidence.append("SEC Edgar")
        negative_1, confidence_1 = fetch_adverse_media(company1, 5)
        negative_2, confidence_2 = fetch_adverse_media(company2, 5)
        if(negative_1 or negative_2):
            supporting_evidence.append("Google news")
        shareholder_sanctions_1 = []
        negative_shareholders = []
        confidence_shareholders = []
        for shareholder in shareholders_1:
            shareholder_sanctions_1.append(check_sanctions(shareholder))
            if(check_sanctions(shareholder) and check_sanctions(shareholder) not in supporting_evidence):
                supporting_evidence.append(check_sanctions(shareholder))
            n, c = fetch_adverse_media(shareholder, 1)     #Checking the top negative news if exists
            if(n is not None):
                if("Google news" not in supporting_evidence):
                    supporting_evidence.append("Google news")
                negative_shareholders.append(n)
                confidence_shareholders.append(c)
        shareholder_sanctions_2 = []
        for shareholder in shareholders_2:
            shareholder_sanctions_2.append(check_sanctions(shareholder))
            if(check_sanctions(shareholder) and check_sanctions(shareholder) not in supporting_evidence):
                supporting_evidence.append(check_sanctions(shareholder))
            n, c = fetch_adverse_media(shareholder, 1)     #Checking the top negative news if exists
            if(n is not None):
                if("Google news" not in supporting_evidence):
                    supporting_evidence.append("Google news")
                negative_shareholders.append(n)
                confidence_shareholders.append(c)
        
        results.append({
            "transaction_id": transaction_id,
            "transaction_details" : transaction_details,
            "Extracted entities": [company1,company2],
            "Entity Type": [company_type_1,company_type_2],
            "Sanctions" : [company1_sanction,company2_sanction],
            "amount": amount,
            "Payer country" : country_1,
            "Receiver country" : country_2,
            "shareholders_company1" : shareholders_1,
            "shareholders_company2" : shareholders_2,
            "shareholders_1_sanctions" : shareholder_sanctions_1,
            "shareholders_2_sanctions" : shareholder_sanctions_2,
            "negative_news_1" : negative_1,
            "negative_news_2" : negative_2,
            "negative_shareholders" : negative_shareholders,
            "confidence_score_1" : confidence_1,
            "confidence_score_2" : confidence_2,
            "confidence_score_shareholders" : confidence_shareholders, 
            "remarks" : remarks,
            "weights" : WEIGHTS,
            "supporting_evidence" : supporting_evidence
        })
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    sample_output = {
        "transaction_id": "TXN001",
        "extracted_entities": ["Apple", "Google"],
        "entity_type": ["Corporation", "Corporation"],
        "risk_score": 0.35,
        "supporting_evidence": ["Found in OFAC", "Negative news detected: Apple"],
        "confidence_score": 0.8,
        "reason": "The transaction between Apple and Google has a risk score of 0.35. Apple is found in the OFAC sanctions list, and there is negative news about Apple. The confidence score is 0.8."
    }
    
    response = model.generate_content(
        f"I am providing you with details of a financial transaction between two entities."
        f"Each detail corresponds to a specific label: _1 means it belongs to Entity 1, and _2 means it belongs to Entity 2."
        f"Sanctions indicate the sanction list an entity is present in, or 'None' if not sanctioned."
        f"Negative news refers to any adverse media coverage about the entity."
        f"Shareholders' sanctions refer to whether any shareholders are sanctioned."
        f"Based on the given weights for different risk factors, calculate the **overall risk score** and **confidence score**."
        f"Then, generate a **summary** explaining why this transaction is classified at that risk level."
        f"Feel free to use info that you might have that is not present in this prompt"
        f"The column remark and transaction_details in input might have some extra info use that in computing risk score and also mention about that as final remark in output"
        f"In the output, give me Transaction ID, both the company names, company types for both, Risk score, The sanction list where they appear/negative news they appear in, confidence score, reason/summary for the score"
        f"For the confidence score give the confidence you have in the risk score you are giving between 0 and 1 also make sure the risk score is 0 to 1 by dividing it by 100"
        f"For the entity type, if you are not able to find the exact type, you can give a general type like Corporation, Individual, NGO etc"
        f"The output should only be json and should be able to be converted from text to json easily and should not contain anything that would cause error in that"
        f"Let me give you an example output, give in this format for each transaction {sample_output}"
        f"The reason doesn't need to follow the exact pattern of sample, keep the language natural and add anymore info you might need to add"
        f"Here is the transaction data: {results}"
    )
    text_output = response.candidates[0].content.parts[0].text
    
    try:
        text_output = text_output.replace("\n", " ").strip()
        json_start = text_output.find("[") if "[" in text_output else text_output.find("{")
        json_end = text_output.rfind("]") + 1 if "]" in text_output else text_output.rfind("}") + 1
        text_output = text_output[json_start:json_end]
    
        json_data = json.loads(text_output)
        if not isinstance(json_data, list):
            json_data = [json_data]
        return json_data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except ValueError as e:
        print(f"Error: {e}")

def process_data(df):
    json_data = process_transactions(df)
    return json_data
