# PiggyBank smart contract. 

## Deploy of a contract
 
 no automation

## Methods

### initcontract()
Initialisation of a contract price matrix and bets time line

### paywinner()
Pay winner and comission

### cleanoldbets()
Clean from bets older then last 5 games to safe RAM

### transfer() 
Handle transfer of EOS bets to the smart contract 

### Automated Test Suite  
1. Install `EOS` and `EOSFactory` based on the guide: `http://eosfactory.io/build/html/tutorials/01.InstallingEOSFactory.html` 
2. Compile contract and put `wasm` and `abi` file to build directory
3. Run `python3 tests/piggybanktest.py` 
