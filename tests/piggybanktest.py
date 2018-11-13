import unittest, argparse, sys, time
from eosfactory.eosf import *
from eosfactory.core import *

verbosity([Verbosity.INFO, Verbosity.OUT, Verbosity.TRACE, Verbosity.DEBUG])

CONTRACT_WORKSPACE = sys.path[0] + "/../"

INITIAL_RAM_KBYTES = 8
INITIAL_STAKE_NET = 3
INITIAL_STAKE_CPU = 3

class Test(unittest.TestCase):

    def stats():
        print_stats(
            [master, host, piggybankbag, alice, carol,piggybankout],
            [
                "core_liquid_balance",
                "ram_usage",
                "ram_quota",
                "total_resources.ram_bytes",
                "self_delegated_bandwidth.net_weight",
                "self_delegated_bandwidth.cpu_weight",
                "total_resources.net_weight",
                "total_resources.cpu_weight",
                "net_limit.available",
                "net_limit.max",
                "net_limit.used",
                "cpu_limit.available",
                "cpu_limit.max",
                "cpu_limit.used"
            ]
        )


    @classmethod
    def setUpClass(cls):
        SCENARIO('''
        There is the ``master`` account that sponsors the ``piggybankbag``
        account equipped with an instance of the ``piggybank`` smart contract. There
        are three players ``alice`` , ``carol`` and ``piggybankout``. We are testing that they make correct bets and winner get rewards.
        ''')

        testnet.verify_production()

        if  testnet.is_local():
            reset()
        
        create_master_account("master", testnet)
        if  testnet.is_local():
            create_account("piggybankbag", master,"piggybankbag",
            buy_ram_kbytes=INITIAL_RAM_KBYTES, stake_net=INITIAL_STAKE_NET, stake_cpu=INITIAL_STAKE_CPU)
        create_account("host", master,"eosio.token",
                       buy_ram_kbytes=INITIAL_RAM_KBYTES, stake_net=INITIAL_STAKE_NET, stake_cpu=INITIAL_STAKE_CPU)
        create_account("alice", piggybankbag,
            buy_ram_kbytes=INITIAL_RAM_KBYTES, stake_net=INITIAL_STAKE_NET, stake_cpu=INITIAL_STAKE_CPU)
        create_account("carol", piggybankbag,
            buy_ram_kbytes=INITIAL_RAM_KBYTES, stake_net=INITIAL_STAKE_NET, stake_cpu=INITIAL_STAKE_CPU)
        create_account("piggybankout", piggybankbag,"piggybankout",
            buy_ram_kbytes=INITIAL_RAM_KBYTES, stake_net=INITIAL_STAKE_NET, stake_cpu=INITIAL_STAKE_CPU)


        if not testnet.is_local():
            cls.stats()

        contract = Contract(piggybankbag, CONTRACT_WORKSPACE)
        contract.build(force=False)

        if testnet.is_local():
            tokenContract =  Contract(host, CONTRACT_WORKSPACE+"../eosio.contracts/build/eosio.token")
            tokenContract.build(force=False)
            tokenContract.deploy(payer=master)

        try:
            contract.deploy(payer=master)
        except errors.ContractRunningError:
            pass


    def setUp(self):
        pass


    def test_01(self):

        COMMENT('''
        Issue and transfer EOS for test purpuses.
        ''')

        if  testnet.is_local():
            host.push_action(
            "create",
            {
                "issuer": master,
                "maximum_supply": "1000000000.0000 EOS",
                "can_freeze": "0",
                "can_recall": "0",
                "can_whitelist": "0"
            },
            permission=[(master, Permission.OWNER), (host, Permission.ACTIVE)])

            host.push_action(
            "issue",
            {
                "to": alice, "quantity": "100.0000 EOS", "memo": ""
            },
            master)

            host.push_action(
            "issue",
            {
                "to": piggybankout, "quantity": "100.0000 EOS", "memo": ""
            },
            master)

            host.push_action(
            "issue",
            {
                "to": carol, "quantity": "100.0000 EOS", "memo": ""
            },
            master)

            host.table("accounts", alice)

            host.table("accounts", carol)
            host.table("accounts", piggybankout)



        COMMENT('''
        Init of the contract:
        WARNING: This action should fail due to authority mismatch!
        ''')
        with self.assertRaises(MissingRequiredAuthorityError):
            piggybankbag.push_action(
                "initcontract", {"user":alice}, permission=(alice, Permission.ACTIVE))

        COMMENT('''
        Attempting to init contract.
        ''')

        piggybankbag.push_action(
            "initcontract", {"user":piggybankbag}, permission=(piggybankbag, Permission.ACTIVE))

        try:
            host.push_action(
                "transfer",
                {
                    "from": alice, "to": piggybankbag,
                    "quantity": "0.5000 EOS", "memo":""
                },
                alice)
        except Error as e:
            if "Bet is incorrect. Please check rules" in e.message:
                COMMENT('''
                Bet should be correct bet.
                ''')


        COMMENT('''
        Transfer first transaction and start game.
        ''')

        host.push_action(
        "transfer",
        {
            "from": alice, "to": piggybankbag,
            "quantity": "1.0000 EOS", "memo":""
        },
        alice)

        time.sleep(3)
        table_activebets =  piggybankbag.table("activebets", piggybankbag)
        table_globalvars = piggybankbag.table("globalvars", piggybankbag)
        table_piggybankbag = host.table("accounts", piggybankbag)
        table_piggybankout = host.table("accounts", piggybankout)
        self.assertEqual(
            table_piggybankbag.json["rows"][0]["balance"], '0.8500 EOS',
        '''assertEqual(table_alice.json["rows"][0]["balance"], '0.8500 EOS')''')
        self.assertEqual(
            table_activebets.json["rows"][0]["bettor"], 'alice',
            '''assertEqual(table_bob.json["rows"][0]["bettor"], 'alice')''')
        self.assertEqual(
        table_activebets.json["rows"][0]["bet_amt"], '10000',
        '''assertEqual(table_bob.json["rows"][0]["bet_amt"], '10000')''')
        self.assertEqual(
            table_piggybankout.json["rows"][0]["balance"], '0.1500 EOS',
            '''assertEqual(table_bob.json["rows"][0]["balance"], '0.1500 EOS')''')
        self.assertEqual(
            table_globalvars.json["rows"][0]["winner"], 'alice',
            '''assertEqual(table_bob.json["rows"][0]["winner"], 'alice')''')
        self.assertEqual(
            table_globalvars.json["rows"][0]["amount"], '10000',
            '''assertEqual(table_bob.json["rows"][0]["amount"], '10000')''')
        self.assertEqual(
            table_globalvars.json["rows"][0]["is_Active"], '1',
            '''assertEqual(table_bob.json["rows"][0]["is_Active"], '1')''')



        COMMENT('''
        Attempting to put wrong bet contract.
        ''')

        try:
            host.push_action(
                "transfer",
                {
                    "from": alice, "to": piggybankbag,
                    "quantity": "0.5000 EOS", "memo":""
                },
                alice)
        except Error as e:
            if "Bet is incorrect. Please check rules" in e.message:
                COMMENT('''
                Bet should be correct bet.
                ''')
            else:
                COMMENT('''
                The error is different than expected.
                ''')
                raise Error(str(e))


        COMMENT('''
        Put second bet.
        ''')

        host.push_action(
            "transfer",
            {
                "from": carol, "to": piggybankbag,
                "quantity": "10.0000 EOS", "memo":"test -alice"
            },
            carol)

        table_activebets = piggybankbag.table("activebets", piggybankbag)
        table_globalvars = piggybankbag.table("globalvars", piggybankbag)
        table_piggybankbag = host.table("accounts", piggybankbag)
        table_piggybankout = host.table("accounts", piggybankout)
        table_alice = host.table("accounts", alice)
        self.assertEqual(
         table_piggybankbag.json["rows"][0]["balance"], '9.3500 EOS',
            '''assertEqual(table_alice.json["rows"][0]["balance"], '9.3500 EOS')''')
        self.assertEqual(
         table_activebets.json["rows"][1]["bettor"], 'carol',
         '''assertEqual(table_bob.json["rows"][0]["bettor"], 'carol')''')
        self.assertEqual(
          table_activebets.json["rows"][1]["bet_amt"], '100000',
          '''assertEqual(table_bob.json["rows"][0]["bet_amt"], '100000')''')
        self.assertEqual(
         table_piggybankout.json["rows"][0]["balance"], '101.1500 EOS',
          '''assertEqual(table_bob.json["rows"][0]["balance"], '101.1500 EOS')''')
        self.assertEqual(
          table_globalvars.json["rows"][0]["winner"], 'carol',
          '''assertEqual(table_bob.json["rows"][0]["winner"], 'carol')''')
        self.assertEqual(
          table_globalvars.json["rows"][0]["amount"], '110000',
          '''assertEqual(table_bob.json["rows"][0]["amount"], '110000')''')
        self.assertEqual(
          table_globalvars.json["rows"][0]["is_Active"], '1',
          '''assertEqual(table_bob.json["rows"][0]["is_Active"], '1')''')
        self.assertEqual(
            table_alice.json["rows"][0]["balance"], '99.5000 EOS',
            '''assertEqual(table_bob.json["rows"][0]["balance"], '99.5000 EOS')''')

        try:
            host.push_action(
                "transfer",
                {
                    "from": alice, "to": piggybankbag,
                    "quantity": "7.0000 EOS", "memo":""
                },
                alice)
        except Error as e:
            if "Bet is incorrect. Please check rules" in e.message:
                COMMENT('''
                Bet should be correct bet.
                ''')
            else:
                COMMENT('''
                The error is different than expected.
                ''')
                raise Error(str(e))

        COMMENT('''
        Check winner method.
        ''')

        piggybankbag.push_action(
            "paywinner", {"user":alice})

        table_globalvars = piggybankbag.table("globalvars", piggybankbag)
        self.assertEqual(
            table_globalvars.json["rows"][0]["is_Active"], '0',
            '''assertEqual(table_bob.json["rows"][0]["is_Active"], '1')''')
        table_carol = host.table("accounts", carol)
        self.assertEqual(
            table_carol.json["rows"][0]["balance"], '109.3500 EOS',
            '''assertEqual(table_alice.json["rows"][0]["balance"], '109.3500 EOS')''')
        table_piggybankbag = host.table("accounts", piggybankbag)
        self.assertEqual(
        table_piggybankbag.json["rows"][0]["balance"], '0.0000 EOS',
        '''assertEqual(table_alice.json["rows"][0]["balance"], '0.0000 EOS')''')



        COMMENT('''
        Check new game created.
        ''')

        host.push_action(
            "transfer",
            {
                "from": alice, "to": piggybankbag,
                "quantity": "10.0000 EOS", "memo":""
            },
            alice)

    time.sleep(3)
    table_activebets =  piggybankbag.table("activebets", piggybankbag)
    table_globalvars = piggybankbag.table("globalvars", piggybankbag)
    table_piggybankbag = host.table("accounts", piggybankbag)
    table_piggybankout = host.table("accounts", piggybankout)
    self.assertEqual(
        table_piggybankbag.json["rows"][0]["balance"], '9.8500 EOS',
        '''assertEqual(table_alice.json["rows"][0]["balance"], '9.8500 EOS')''')
    self.assertEqual(
        table_activebets.json["rows"][0]["bettor"], 'alice',
        '''assertEqual(table_bob.json["rows"][0]["bettor"], 'alice')''')
    self.assertEqual(
        table_activebets.json["rows"][0]["bet_amt"], '100000',
        '''assertEqual(table_bob.json["rows"][0]["bet_amt"], '100000')''')
    self.assertEqual(
        table_piggybankout.json["rows"][0]["balance"], '109.6500 EOS',
        '''assertEqual(table_bob.json["rows"][0]["balance"], '109.6500 EOS')''')
    self.assertEqual(
        table_globalvars.json["rows"][1]["winner"], 'alice',
        '''assertEqual(table_bob.json["rows"][0]["winner"], 'alice')''')
    self.assertEqual(
        table_globalvars.json["rows"][1]["amount"], '100000',
        '''assertEqual(table_bob.json["rows"][0]["amount"], '100000')''')
    self.assertEqual(
        table_globalvars.json["rows"][1]["is_Active"], '1',
        '''assertEqual(table_bob.json["rows"][0]["is_Active"], '1')''')





    def tearDown(self):
        pass


    @classmethod
    def tearDownClass(cls):
        if testnet.is_local():
            stop()
        else:
            cls.stats()


testnet = None

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='''
    This is a unit test for the ``piggybank`` smart contract.
    It works both on a local testnet and remote testnet.
    The default option is local testnet.
    ''')

    parser.add_argument(
        "alias", nargs="?",
        help="Testnet alias")

    parser.add_argument(
        "-t", "--testnet", nargs=4,
        help="<url> <name> <owner key> <active key>")

    parser.add_argument(
        "-r", "--reset", action="store_true",
        help="Reset testnet cache")

    args = parser.parse_args()

    testnet = get_testnet(args.alias, args.testnet, reset=args.reset)
    testnet.configure()

    if args.reset and not testnet.is_local():
        testnet.clear_cache()

    unittest.main(argv=[sys.argv[0]])
