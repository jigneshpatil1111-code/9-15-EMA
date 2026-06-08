import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.broker_factory import get_broker

def main():
    broker = get_broker()
    broker.initialize()
    print("Testing quote_data format:")
    response = broker._client.quote_data({"NSE_EQ": ["1333"]})
    print(response)

if __name__ == "__main__":
    main()
