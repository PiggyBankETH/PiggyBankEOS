#include <eosiolib/eosio.hpp>
#include <eosiolib/contract.hpp>
#include <eosiolib/asset.hpp>
#include <eosiolib/time.hpp>
#include <eosiolib/multi_index.hpp>
#include "logger.hpp"
#include <utility>

//Remove before production deploy
//#define DEBUG

using namespace eosio;

CONTRACT piggybank
:
public eosio::contract{

private:


void start_new_game(uint64_t id_of_last_game_id, uint64_t timer_value, name bettor, uint64_t amount) {
    uint32_t nowTime = now();
    globalvars.emplace(_self, [&](auto &g) {
        g.game_id = id_of_last_game_id + 1;
        g.start_game_time = nowTime;
        g.end_game_time = nowTime + timer_value;
        g.winner = bettor;
        g.is_Active = 1;
        g.amount = amount;
    });
}

void end_game_and_pay(uint64_t game_id) {

    const auto game_itr = globalvars.find(game_id);

    name winner = game_itr->winner;
    uint64_t amount = game_itr->amount;


    asset assetToPayWinner = eosio::asset(amount * 0.85, symbol(symbol_code("EOS"), 4));

    //Pay to winner
    action(
            permission_level{get_self(), "active"_n},
            "eosio.token"_n,
            "transfer"_n,
            std::make_tuple(
                    _self,
                    winner,
                    assetToPayWinner,
                    std::string("Game winner reward")
            )
    ).send();

    globalvars.modify(game_itr, get_self(), [&](auto &s) {
        s.is_Active = 0;
    });

}


void store_bet_and_pay_referral(name bettor, name referral, uint64_t amount, uint64_t bet_number, uint64_t game_id) {

    uint32_t nowTime = now();
    //Add bet to bet table
    betsvars.emplace(_self, [&](auto &b) {
        b.id = betsvars.available_primary_key();
        b.bettor = bettor;
        b.referral = referral;
        b.bet_amt = amount;
        b.bet_number = bet_number;
        b.game_id = game_id;
        b.bet_time = nowTime;
    });


    if (referral == "piggybankout"_n) {

        //No referral. Pay commission 15%
        asset assetToPayRef = eosio::asset(amount * 0.15, symbol(symbol_code("EOS"), 4));

        action(
                permission_level{get_self(), "active"_n},
                "eosio.token"_n,
                "transfer"_n,
                std::make_tuple(
                        _self,
                        referral,
                        assetToPayRef,
                        std::string("Commission 15% cashback")
                )
        ).send();
    } else {
        //Pay referral 5% and commission 10%
        asset assetToPayRef = eosio::asset(amount * 0.05, symbol(symbol_code("EOS"), 4));

        action(
                permission_level{get_self(), "active"_n},
                "eosio.token"_n,
                "transfer"_n,
                std::make_tuple(
                        _self,
                        referral,
                        assetToPayRef,
                        std::string("Referral 5% cashback")
                )
        ).send();

        asset assetToPayCom = eosio::asset(amount * 0.10, symbol(symbol_code("EOS"), 4));

        action(
                permission_level{get_self(), "active"_n},
                "eosio.token"_n,
                "transfer"_n,
                std::make_tuple(
                        _self,
                        "piggybankout"_n,
                        assetToPayCom,
                        std::string("Commission 10% cashback")
                )
        ).send();
    }
}


public:

using contract::contract;

//constructor
piggybank(name
receiver,
name code, datastream<const char *>
ds):
contract(receiver, code, ds
),
globalvars(_self, _self
.value),
betsvars(_self, _self
.value)
{
}




ACTION initcontract() {

    logger_info("initcontract ");
    require_auth("piggybankbag"_n);

    pricetable();

}


ACTION paywinner() {

    logger_info("paywinner");

    uint32_t nowTime = now();
    for (const auto &globalvar :globalvars) {
        if (globalvar.is_Active == 1 && nowTime >= globalvar.end_game_time) {
            //Game ended. Need to pay winner and make it inactive
            end_game_and_pay(globalvar.game_id);
        }
    }

}

ACTION cleanoldbets() {

    logger_info("cleanoldbets");

    require_auth("piggybankbag"_n);

    //Get last game id
    uint64_t last_game_id = -1;

    auto itr = globalvars.begin();
    if (itr != globalvars.end()) {
        last_game_id = (--globalvars.end())->game_id;
    }

    if (last_game_id > 5) {
        //Find items which are from games older then 5 last one
        uint32_t max_game_id_to_clean = last_game_id - 5;
        std::vector<uint64_t> keysForDeletion;
        for (const bet &item :betsvars) {

            if (item.game_id <= max_game_id_to_clean) {
                keysForDeletion.push_back(item.id);
            }
        }
        //Now delete each item from bets table
        for (uint64_t key : keysForDeletion) {
            auto itr = betsvars.find(key);
            if (itr != betsvars.end()) {
                betsvars.erase(itr);
            }
        }
    }

}


ACTION transfer(uint64_t sender, uint64_t receiver) {

    auto transfer_data = unpack_action_data<st_transfer>();

    logger_info("transfer() sender:", name(sender), " receiver:", name(receiver), " quantity: ", transfer_data.quantity,
                " memo: ", transfer_data.memo);

    //Don't accept transaction from self
    if (transfer_data.from == _self || transfer_data.from == "piggybankbag"_n) {
        return;
    }

    asset amount = transfer_data.quantity;

    eosio_assert(amount.is_valid(), "Invalid asset");

    //Get possible referral user from memo of transaction
    std::string ref_str;

    const std::size_t first_break = transfer_data.memo.find("-");

    if (first_break != std::string::npos) {

        const std::string after_first_break = transfer_data.memo.substr(first_break + 1);
        const std::size_t second_break = after_first_break.find("-");

        if (second_break != std::string::npos) {

            ref_str = after_first_break.substr(0, second_break);
        } else {

            ref_str = after_first_break;
        }
    } else {
        ref_str = std::string("");
    }

    name
    referral = "piggybankout"_n;

    const name possible_ref = name(ref_str);

    if (possible_ref != _self && possible_ref != transfer_data.from && is_account(possible_ref)) {
        referral = possible_ref;
    }

    //Check if bet is in range of price matrix and in range of available options
    price_table table = pricetable();
    int matched = 0;
    int betNumber = 0;
    for (const auto &element :table) {
        if (element.bet_amt == amount.amount) {
            matched = 1;
            betNumber = element.bet_number;
            break;
        }
    }

    if (matched == 0) {
        eosio_assert(0, "Bet is not matched price matrix. Please check rules");

    }

    const pricematrix &element = table.get(betNumber);

    eosio_assert(element.bet_timer > 0, "Timer valuer for such bet is empty");

    uint32_t nowTime = now();

    //Check if any game is active right now and get current game id

    uint64_t last_game_id = -1;

    auto itr = globalvars.begin();
    if (itr != globalvars.end()) {
        last_game_id = (--globalvars.end())->game_id;
    }

    if (last_game_id == -1) {
        //This is first game in a contract
        start_new_game(last_game_id, element.bet_timer, transfer_data.from, amount.amount);
        last_game_id = 0;
    }

    bool newGame = 0;
    //Check if last game already ended
    const auto game_itr = (--globalvars.end());

    if (nowTime >= game_itr->end_game_time) {

        //Start new game
        start_new_game(last_game_id, element.bet_timer, transfer_data.from, amount.amount);
        last_game_id++;
        newGame = 1;
    }

    if (betsvars.begin() == betsvars.end() || newGame == 1) {

        //This is first bet in a contract or new game
        store_bet_and_pay_referral(transfer_data.from, referral, amount.amount, betNumber, last_game_id);

    } else {

        //Check if current bet either bigger then last one or not lower then 2 above in matrix
        const auto last_bet_itr = --(betsvars.end());
        if (betNumber >= (last_bet_itr->bet_number) - 2.0) {

            //Bet is correct. Save it
            store_bet_and_pay_referral(transfer_data.from, referral, amount.amount, betNumber, last_game_id);

            //Modify current game values based on the last bet
            globalvars.modify(globalvars.find(last_game_id), get_self(), [&](auto &s) {
                s.amount += amount.amount;
                s.winner = transfer_data.from;
                s.end_game_time = nowTime + element.bet_timer;

            });
        } else {
            eosio_assert(0, "Bet is incorrect. Please check rules");
        }
    }
}


private:


// taken from eosio.token.hpp
struct st_transfer {
    name from;
    name to;
    asset quantity;
    std::string memo;
};


TABLE pricematrix{
        uint64_t  bet_number;
        uint64_t  bet_amt;
        uint64_t  bet_timer;
        uint64_t  primary_key() const { return bet_number; }

        EOSLIB_SERIALIZE(pricematrix, (bet_number)(bet_amt)(bet_timer))
};

typedef eosio::multi_index<"pricematrix"_n, pricematrix> price_table;

TABLE bet{
        uint64_t        id;
        name            bettor;
        name            referral;
        uint64_t        bet_amt;
        uint64_t        bet_number;
        uint64_t        game_id;
        uint64_t        bet_time;

        uint64_t        primary_key() const { return id; }

        EOSLIB_SERIALIZE(bet, (id)(bettor)(referral)(bet_amt)(bet_number)(game_id)(bet_time))
};

typedef eosio::multi_index<"activebets"_n, bet> bets_index;

//table to store current game details
TABLE globalvar{
        uint64_t        game_id;
        uint64_t        start_game_time;
        uint64_t        end_game_time;
        uint64_t        is_Active;
        name            winner;
        uint64_t        amount;

        uint64_t        primary_key() const { return game_id; }

        EOSLIB_SERIALIZE(globalvar, (game_id)(start_game_time)(end_game_time)(is_Active)(winner)(amount))
};

typedef eosio::multi_index<"globalvars"_n, globalvar> globalvars_index;


globalvars_index globalvars;
bets_index betsvars;


price_table pricetable() {

    price_table t(_self, _self.value);
    //Check if price table already exist and created for the contract
    auto itr = t.find(1);
    if (itr != t.end()) {
        return t;
    }

    //Initialization of bet matrix
    uint64_t hours = 24;
    //First 22 bets values differ by 1 from 1st till 22nd
    for (int i = 1; i <= 22; ++i) {
        t.emplace(get_self(), [&](auto &p) {
            p.bet_number = i;
            p.bet_amt = i * 10000; //1-22 EOS
            p.bet_timer = hours * 60 * 60;
            hours--;
        });
    }

    //23d values
    t.emplace(get_self(), [&](auto &p) {
        p.bet_number = 23;
        p.bet_amt = 25 * 10000; //25 EOS
        p.bet_timer = 2 * 60 * 60; // 2 hours
    });
    //24th values
    t.emplace(get_self(), [&](auto &p) {
        p.bet_number = 24;
        p.bet_amt = 50 * 10000; //50 EOS
        p.bet_timer = 1 * 60 * 60; // 1 hour
    });
    //25th values
    t.emplace(get_self(), [&](auto &p) {
        p.bet_number = 25;
        p.bet_amt = 100 * 10000; //100 EOS
        p.bet_timer = 40 * 60; // 40 minute
    });
    //26th values
    t.emplace(get_self(), [&](auto &p) {
        p.bet_number = 26;
        p.bet_amt = 500 * 10000; //500 EOS
        p.bet_timer = 20 * 60; // 20 minute
    });
    //27th values
    t.emplace(get_self(), [&](auto &p) {
        p.bet_number = 27;
        p.bet_amt = 1000 * 10000; //1000 EOS
        p.bet_timer = 10 * 60; // 10 minute
    });
    //28th values
    t.emplace(get_self(), [&](auto &p) {
        p.bet_number = 28;
        p.bet_amt = 5000 * 10000; //5000 EOS
        p.bet_timer = 5 * 60; // 5 minute
    });

    return t;
}

};



#define EOSIO_DISPATCH_CUSTOM(TYPE, MEMBERS) \
extern "C" { \
   void apply( uint64_t receiver, uint64_t code, uint64_t action ) { \
   auto self = receiver; \
      if( code == self ||  code == name("eosio.token").value) { \
       if( action == name("transfer").value){ \
            eosio_assert( code == name("eosio.token").value, "Must transfer EOS"); \
         } \
        switch( action ) { \
            EOSIO_DISPATCH_HELPER( TYPE, MEMBERS ) \
         } \
         /* does not allow destructor of this contract to run: eosio_exit(0); */ \
      } \
   } \
} \

EOSIO_DISPATCH_CUSTOM(piggybank, (initcontract)(paywinner)(cleanoldbets)(transfer)(erase))

