import re
import pandas as pd

def parse_transaction_file(content):
    transaction_id = re.search(r"Transaction ID:\s*(.+)", content)
    payer_name = re.search(r'Sender:\s*- Name: "(.*?)"', content)
    payer_address = re.search(r"- Address: (.+)", content)
    receiver_name = re.search(r'Receiver:\s*- Name: "(.*?)"', content)
    receiver_address = re.search(r"- Address: (.+)", content)
    amount = re.search(r"Amount:\s*\$([\d,]+\.\d+)", content)
    transaction_details = re.search(r'Notes: "(.*?)"', content)

    additional_notes = re.findall(r'- "(.*?)"', content)
    remarks = ", ".join(additional_notes) if additional_notes else "N/A"

    payer_address = payer_address.group(1).strip()
    payer_country_match = re.search(r'([A-Za-z\s]+)$', payer_address)
    receiver_address = receiver_address.group(1).strip()
    receiver_country_match = re.search(r'([A-Za-z\s]+)$', receiver_address)

    payer_country = payer_country_match.group(1) if payer_country_match else ""
    receiver_country = receiver_country_match.group(1) if receiver_country_match else ""

    transaction_id = transaction_id.group(1) if transaction_id else ""
    payer_name = payer_name.group(1) if payer_name else ""
    receiver_name = receiver_name.group(1) if receiver_name else ""
    amount = amount.group(1) if amount else ""
    transaction_details = transaction_details.group(1) if transaction_details else ""
    headers = [
    "Transaction ID",
    "Payer Name",
    "Payer Country",
    "Receiver Name",
    "Receiver Country",
    "Transaction Details",
    "Amount",
    "Remarks",]
    data = [[transaction_id,
        payer_name,
        payer_country,
        receiver_name,
        receiver_country,
        transaction_details,  
        amount,
        remarks]]
    transaction_data = pd.DataFrame(data, columns=headers)
    return transaction_data
