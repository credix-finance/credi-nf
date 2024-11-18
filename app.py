import streamlit as st
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import uuid
import os
import re

st.title("Nota Fiscal Generator")


def clean_cnpj(cnpj):
    return re.sub(r'[./-]', '', cnpj)


def generate_unique_id():
    unique_number = uuid.uuid4().int >> 64
    return f"NFe{unique_number:044d}"


def replace_names(root):
    fake_names = {
        "FREXCO": "FAKECO",
        "FREXCO COMERCIO E DISTRIBUICAO DE  ALIME": "FAKECO COMERCIO E DISTRIBUICAO DE ALIME",
        "GM TECNOLOGIA LTDA": "FAKE TECNOLOGIA LTDA",
        "Rodrigo de Almeida Sartorio": "João da Silva",
        "maxim@credix.finance": "fake@credix.finance",
        "resp_tecnico_dfe_protheus@totvs.com.br": "tech_support@fakecompany.com"
    }

    for elem in root.findall('.//emit/xNome'):
        elem.text = fake_names["FREXCO"]
    for elem in root.findall('.//emit/xFant'):
        elem.text = fake_names["FREXCO COMERCIO E DISTRIBUICAO DE  ALIME"]
    for elem in root.findall('.//dest/xNome'):
        elem.text = fake_names["GM TECNOLOGIA LTDA"]
    for elem in root.findall('.//infRespTec/xContato'):
        elem.text = fake_names["Rodrigo de Almeida Sartorio"]
    for elem in root.findall('.//dest/email'):
        elem.text = fake_names["maxim@credix.finance"]
    for elem in root.findall('.//infRespTec/email'):
        elem.text = fake_names["resp_tecnico_dfe_protheus@totvs.com.br"]


# Path to the original NF XML file
xml_file_path = os.path.join("templates", "nfe-order-details.mock.xml")

# Load the original NF XML
tree = ET.parse(xml_file_path)
root = tree.getroot()

# Remove namespaces
for elem in root.iter():
    elem.tag = elem.tag.split('}', 1)[1] if '}' in elem.tag else elem.tag

st.markdown("---")  # Divider
# Input fields for CNPJ
seller_cnpj = st.text_input("Seller CNPJ", value="30.792.427/0001-30")
buyer_cnpj = st.text_input("Buyer CNPJ", value="30.998.254/0033-99")

st.markdown("---")  # Divider

# Input fields for Buyer Address
buyer_address = {
    "Street": st.text_input("Street", value="JOAQUIM FLORIANO 100"),
    "Number": st.text_input("Number", value="100"),
    "Neighborhood": st.text_input("Neighborhood", value="CENTRO"),
    "Municipality": st.text_input("Municipality", value="3550308"),
    "City": st.text_input("City", value="SAO PAULO"),
    "State": st.text_input("State", value="SP"),
    "CEP": st.text_input("CEP", value="04534000"),
    "Country Code": st.text_input("Country Code", value="1058"),
    "Country": st.text_input("Country", value="BRASIL")
}

st.markdown("---")  # Divider

# Input fields for installments
num_installments = st.number_input("Number of Installments", min_value=1, step=1)
installment_details = []

default_due_date = datetime.now() + timedelta(days=7)
for i in range(num_installments):
    st.write(f"Installment {i + 1}")
    amount = st.number_input(f"Installment Amount {i + 1}", min_value=0.0, step=0.01, value=100.0, key=f"amount_{i}")
    due_date = st.date_input(f"Due Date {i + 1}", value=default_due_date + timedelta(days=7 * i), key=f"date_{i}")
    installment_details.append((amount, due_date))

st.markdown("---")  # Divider

if st.button("Generate Nota Fiscal"):
    # Clean CNPJs
    seller_cnpj_clean = clean_cnpj(seller_cnpj)
    buyer_cnpj_clean = clean_cnpj(buyer_cnpj)

    # Update XML fields
    root.find('.//emit/CNPJ').text = seller_cnpj_clean
    root.find('.//dest/CNPJ').text = buyer_cnpj_clean

    # Update buyer address fields
    root.find('.//enderDest/xLgr').text = buyer_address["Street"]
    root.find('.//enderDest/nro').text = buyer_address["Number"]
    root.find('.//enderDest/xBairro').text = buyer_address["Neighborhood"]
    root.find('.//enderDest/cMun').text = buyer_address["Municipality"]
    root.find('.//enderDest/xMun').text = buyer_address["City"]
    root.find('.//enderDest/UF').text = buyer_address["State"]
    root.find('.//enderDest/CEP').text = buyer_address["CEP"]
    root.find('.//enderDest/cPais').text = buyer_address["Country Code"]
    root.find('.//enderDest/xPais').text = buyer_address["Country"]

    # Clear existing installments
    for dup in root.findall('.//dup'):
        root.find('.//cobr').remove(dup)

    # Add new installments
    total_value = 0
    for i, (amount, due_date) in enumerate(installment_details):
        total_value += amount
        dup = ET.SubElement(root.find('.//cobr'), 'dup')
        nDup = ET.SubElement(dup, 'nDup')
        nDup.text = f"{i+1:03}"
        dVenc = ET.SubElement(dup, 'dVenc')
        dVenc.text = due_date.strftime("%Y-%m-%d")
        vDup = ET.SubElement(dup, 'vDup')
        vDup.text = f"{amount:.2f}"

    # Update unique NF number and ID
    root.find('.//infNFe').set('Id', generate_unique_id())

    # Replace names in the XML
    replace_names(root)

    # Update date fields to today's date
    today = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    root.find('.//dhRecbto').text = today
    root.find('.//dhEmi').text = today
    root.find('.//dhSaiEnt').text = today

    # Update total values
    total_value_str = f"{total_value:.2f}"
    root.find('.//vBC').text = total_value_str
    root.find('.//vProd').text = total_value_str
    root.find('.//vNF').text = total_value_str
    root.find('.//fat/vOrig').text = total_value_str
    root.find('.//fat/vLiq').text = total_value_str
    root.find('.//detPag/vPag').text = total_value_str

    # Save the modified XML to a new file
    new_xml_file_path = f"generated_nota_fiscal_{uuid.uuid4().int >> 64}.xml"
    tree.write(new_xml_file_path, encoding="utf-8", xml_declaration=True)

    st.success(f"Nota Fiscal generated and saved as {new_xml_file_path}")

    # Provide a download link
    with open(new_xml_file_path, "rb") as file:
        btn = st.download_button(
            label="Download Nota Fiscal",
            data=file,
            file_name=new_xml_file_path,
            mime="application/xml"
        )
