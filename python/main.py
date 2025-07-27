from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

# Node access params
RPC_URL = "http://alice:password@127.0.0.1:18443"

def main():
    try:
        # General client for non-wallet-specific commands
        client = AuthServiceProxy(RPC_URL)

        # Get blockchain info
        blockchain_info = client.getblockchaininfo()
        print("Blockchain Info:", blockchain_info)

        # Create/Load the wallets, named 'Miner' and 'Trader'. Have logic to optionally create/load them if they do not exist or are not loaded already.
        
        # Check if Miner wallet exists and create/load it
        try:
            client.loadwallet("Miner")
            print("Miner wallet loaded")
        except JSONRPCException as e:
            if "Wallet file not found" in str(e) or "does not exist" in str(e):
                try:
                    client.createwallet("Miner")
                    print("Miner wallet created")
                except JSONRPCException as create_error:
                    if "already exists" in str(create_error):
                        print("Miner wallet already exists")
                    else:
                        raise create_error
            elif "already loaded" in str(e):
                print("Miner wallet already loaded")
            else:
                raise e

        # Check if Trader wallet exists and create/load it
        try:
            client.loadwallet("Trader")
            print("Trader wallet loaded")
        except JSONRPCException as e:
            if "Wallet file not found" in str(e) or "does not exist" in str(e):
                try:
                    client.createwallet("Trader")
                    print("Trader wallet created")
                except JSONRPCException as create_error:
                    if "already exists" in str(create_error):
                        print("Trader wallet already exists")
                    else:
                        raise create_error
            elif "already loaded" in str(e):
                print("Trader wallet already loaded")
            else:
                raise e

        # Create wallet-specific RPC clients
        miner_client = AuthServiceProxy(RPC_URL + "/wallet/Miner")
        trader_client = AuthServiceProxy(RPC_URL + "/wallet/Trader")

        # Generate spendable balances in the Miner wallet. Determine how many blocks need to be mined.
        
        # Generate an address from Miner wallet with label "Mining Reward"
        mining_address = miner_client.getnewaddress("Mining Reward")
        print(f"Miner mining address: {mining_address}")

        # Mine blocks until we get a positive spendable balance
        # In regtest, coinbase rewards require 100 confirmations to be spendable
        print("Mining blocks to generate spendable balance...")
        blocks_mined = 0
        
        while True:
            # Mine one block to the mining address
            block_hashes = client.generatetoaddress(1, mining_address)
            blocks_mined += 1
            
            # Check spendable balance
            balance = miner_client.getbalance()
            print(f"Blocks mined: {blocks_mined}, Spendable balance: {balance} BTC")
            
            # Break when we have a positive balance (this happens after 101 blocks in regtest)
            if balance > 0:
                break

        """
        Comment on wallet balance behavior:
        In Bitcoin regtest mode, newly mined block rewards (coinbase transactions) 
        require 100 confirmations before they become spendable. This is why we need 
        to mine 101 blocks total - the first block creates a reward, but it only 
        becomes spendable after 100 additional blocks are mined on top of it.
        This maturity period prevents spending coins from potentially orphaned blocks.
        """

        print(f"Final Miner wallet balance: {miner_client.getbalance()} BTC")

        # Load the Trader wallet and generate a new address.
        trader_address = trader_client.getnewaddress("Received")
        print(f"Trader receiving address: {trader_address}")

        # Send 20 BTC from Miner to Trader.
        print("Sending 20 BTC from Miner to Trader...")
        txid = miner_client.sendtoaddress(trader_address, 20)
        print(f"Transaction sent with TXID: {txid}")

        # Check the transaction in the mempool.
        print("Fetching transaction from mempool...")
        try:
            mempool_entry = client.getmempoolentry(txid)
            print(f"Transaction found in mempool: {txid}")
            print(f"Mempool entry fee: {mempool_entry.get('fee', 'N/A')} BTC")
        except JSONRPCException as e:
            print(f"Error fetching mempool entry: {e}")

        # Mine 1 block to confirm the transaction.
        print("Mining 1 block to confirm the transaction...")
        confirmation_blocks = client.generatetoaddress(1, mining_address)
        confirmation_block_hash = confirmation_blocks[0]
        print(f"Transaction confirmed in block: {confirmation_block_hash}")

        # Extract all required transaction details.
        print("Extracting transaction details...")
        
        # Get the raw transaction with verbose output
        raw_tx = client.getrawtransaction(txid, True)
        
        # Get transaction details from wallet perspective
        tx_details = miner_client.gettransaction(txid)
        
        # Extract input information (from Miner)
        # The input references a previous transaction output
        input_txid = raw_tx['vin'][0]['txid']
        input_vout = raw_tx['vin'][0]['vout']
        
        # Get the previous transaction to find input details
        input_raw_tx = client.getrawtransaction(input_txid, True)
        miner_input_address = input_raw_tx['vout'][input_vout]['scriptPubKey']['address']
        miner_input_amount = input_raw_tx['vout'][input_vout]['value']
        
        # Extract output information
        trader_output_address = None
        trader_output_amount = None
        miner_change_address = None
        miner_change_amount = None
        
        # Parse outputs - one goes to trader, one is change back to miner
        for vout in raw_tx['vout']:
            address = vout['scriptPubKey']['address']
            amount = vout['value']
            
            if address == trader_address:
                trader_output_address = address
                trader_output_amount = amount
            else:
                # This is the change output back to miner
                miner_change_address = address
                miner_change_amount = amount
        
        # Calculate transaction fees (input - outputs)
        total_output = (trader_output_amount or 0) + (miner_change_amount or 0)
        transaction_fees = miner_input_amount - total_output
        
        # Get block height and hash where transaction was confirmed
        current_block_height = client.getblockcount()
        current_block_hash = client.getblockhash(current_block_height)

        # Write the data to ../out.txt in the specified format given in readme.md.
        output_data = [
            txid,  # Transaction ID (txid)
            miner_input_address,  # Miner's Input Address
            str(miner_input_amount),  # Miner's Input Amount (in BTC)
            trader_output_address,  # Trader's Output Address
            str(trader_output_amount),  # Trader's Output Amount (in BTC)
            miner_change_address,  # Miner's Change Address
            str(miner_change_amount),  # Miner's Change Amount (in BTC)
            str(transaction_fees),  # Transaction Fees (in BTC)
            str(current_block_height),  # Block height at which the transaction is confirmed
            current_block_hash  # Block hash at which the transaction is confirmed
        ]
        
        # Write to out.txt file
        with open('../out.txt', 'w') as f:
            for line in output_data:
                f.write(f"{line}\n")
        
        print("Transaction details written to ../out.txt")
        print("Process completed successfully!")
        
        # Print summary for verification
        print("\n=== TRANSACTION SUMMARY ===")
        print(f"Transaction ID: {txid}")
        print(f"Miner Input: {miner_input_address} ({miner_input_amount} BTC)")
        print(f"Trader Output: {trader_output_address} ({trader_output_amount} BTC)")
        print(f"Miner Change: {miner_change_address} ({miner_change_amount} BTC)")
        print(f"Transaction Fee: {transaction_fees} BTC")
        print(f"Confirmed in block {current_block_height}: {current_block_hash}")

    except Exception as e:
        print("Error occurred: {}".format(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()























































































# from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

# # Node access params
# RPC_URL = "http://alice:password@127.0.0.1:18443"

# def main():
#     try:
#         # General client for non-wallet-specific commands
#         client = AuthServiceProxy(RPC_URL)

#         # Get blockchain info
#         blockchain_info = client.getblockchaininfo()

#         print("Blockchain Info:", blockchain_info)

#         # Create/Load the wallets, named 'Miner' and 'Trader'. Have logic to optionally create/load them if they do not exist or are not loaded already.

#         # Generate spendable balances in the Miner wallet. Determine how many blocks need to be mined.

#         # Load the Trader wallet and generate a new address.

#         # Send 20 BTC from Miner to Trader.

#         # Check the transaction in the mempool.

#         # Mine 1 block to confirm the transaction.

#         # Extract all required transaction details.

#         # Write the data to ../out.txt in the specified format given in readme.md.
#     except Exception as e:
#         print("Error occurred: {}".format(e))

# if __name__ == "__main__":
#     main()
