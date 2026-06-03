from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_storage("google-ads.yaml")
customer_service = client.get_service("CustomerService")

customer = client.get_type("Customer")
customer.descriptive_name = "Test Client Account"
customer.currency_code = "INR"
customer.time_zone = "Asia/Kolkata"
customer.test_account = True

response = customer_service.create_customer_client(
    customer_id="3447764460",
    customer_client=customer
)

print(f"Test Client ID: {response.resource_name.split('/')[1]}")