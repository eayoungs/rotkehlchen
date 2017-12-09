import os
import csv
from rotkelchen.utils import tsToDate


class CSVExporter(object):

    def __init__(self, profit_currency, logger, create_csv):
        self.profit_currency = profit_currency
        self.log = logger
        self.create_csv = create_csv

        if create_csv:
            self.trades_csv = list()
            self.loan_profits_csv = list()
            self.asset_movements_csv = list()
            self.tx_gas_costs_csv = list()
            self.margin_positions_csv = list()
            self.loan_settlements_csv = list()
            self.all_events_csv = list()

    def dict_to_csv_file(self, path, dictionary_list):

        if len(dictionary_list) == 0:
            self.log.logdebug("Skipping writting empty CSV for {}".format(path))
            return

        with open(path, 'w') as f:
            w = csv.DictWriter(f, dictionary_list[0].keys())
            w.writeheader()
            for dic in dictionary_list:
                w.writerow(dic)

    def add_to_allevents(
            self,
            event_type,
            paid_in_profit_currency,
            paid_asset,
            paid_in_asset,
            received_asset,
            received_in_asset,
            received_in_profit_currency,
            timestamp,
            is_virtual=False,
            taxable_amount='',
            taxable_bought_cost='',
    ):
        row = len(self.all_events_csv) + 2
        net_profit_or_loss = 0  # no profit by buying
        if event_type == 'sell':
            net_profit_or_loss = '=IF(E{}=0,0,H{}-E{})'.format(row, row, row)
            net_profit_or_loss = '=H{}-F{}'.format(row, row)
        elif event_type in ('tx_gas_cost', 'asset_movement', 'loan_settlement'):
            net_profit_or_loss = '=-B{}'.format(row)
        elif event_type in ('interest_rate_payment', 'margin_position_close'):
            net_profit_or_loss = '=H{}'.format(row)

        self.all_events_csv.append({
            'type': event_type,
            'paid_in_{}'.format(self.profit_currency): paid_in_profit_currency,
            'paid_asset': paid_asset,
            'paid_in_asset': paid_in_asset,
            'taxable_amount': taxable_amount,
            'taxable_bought_cost': taxable_bought_cost,
            'received_asset': received_asset,
            'received_in_{}'.format(self.profit_currency): received_in_profit_currency,
            'received_in_asset': received_in_asset,
            'net_profit_or_loss': net_profit_or_loss,
            'time': tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'is_virtual': is_virtual
        })

    def add_buy(
            self,
            bought_asset,
            rate,
            fee_cost,
            amount,
            gross_cost,
            cost,
            paid_with_asset,
            paid_with_asset_rate,
            timestamp,
            is_virtual,
    ):
        if not self.create_csv:
            return

        self.trades_csv.append({
            'type': 'buy',
            'asset': bought_asset,
            "price_in_{}".format(self.profit_currency): rate,
            "fee_in_{}".format(self.profit_currency): fee_cost,
            "amount": amount,
            "gross_gained_or_invested_{}".format(self.profit_currency): gross_cost,
            "net_gained_or_invested_{}".format(self.profit_currency): cost,
            "exchanged_for": paid_with_asset,
            "exchanged_asset_euro_exchange_rate": paid_with_asset_rate,
            "time": tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            "is_virtual": is_virtual
        })
        self.add_to_allevents(
            event_type='buy',
            paid_in_profit_currency=cost,
            paid_asset=self.profit_currency,
            paid_in_asset=cost,
            received_asset=bought_asset,
            received_in_asset=amount,
            received_in_profit_currency=0,
            timestamp=timestamp,
            is_virtual=is_virtual
        )

    def add_sell(
            self,
            selling_asset,
            rate_in_profit_currency,
            total_fee_in_profit_currency,
            gain_in_profit_currency,
            selling_amount,
            receiving_asset,
            receiving_amount,
            receiving_asset_rate_in_profit_currency,
            taxable_amount,
            taxable_bought_cost,
            timestamp,
            is_virtual,
    ):
        if not self.create_csv:
            return

        self.trades_csv.append({
            'type': 'sell',
            'asset': selling_asset,
            "price_in_{}".format(self.profit_currency): rate_in_profit_currency,
            "fee_in_{}".format(self.profit_currency): total_fee_in_profit_currency,
            "gross_gained_or_invested_{}".format(self.profit_currency): gain_in_profit_currency + total_fee_in_profit_currency,
            "net_gained_or_invested_{}".format(self.profit_currency): gain_in_profit_currency,
            "amount": selling_amount,
            "exchanged_for": receiving_asset,
            "exchanged_asset_euro_exchange_rate": receiving_asset_rate_in_profit_currency,
            "time": tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            "is_virtual": is_virtual,
        })
        self.add_to_allevents(
            event_type='sell',
            paid_in_profit_currency=selling_amount * rate_in_profit_currency + total_fee_in_profit_currency,
            paid_asset=selling_asset,
            paid_in_asset=selling_amount,
            received_asset=receiving_asset,
            received_in_asset=receiving_amount,
            received_in_profit_currency=receiving_asset_rate_in_profit_currency * receiving_amount,
            timestamp=timestamp,
            is_virtual=is_virtual,
            taxable_amount=taxable_amount,
            taxable_bought_cost=taxable_bought_cost,
        )

    def add_loan_settlement(
            self,
            asset,
            amount,
            rate_in_profit_currency,
            total_fee_in_profit_currency,
            timestamp,
    ):
        if not self.create_csv:
            return

        self.loan_settlements_csv.append({
            'asset': asset,
            "amount": amount,
            "price_in_{}".format(self.profit_currency): rate_in_profit_currency,
            "fee_in_{}".format(self.profit_currency): total_fee_in_profit_currency,
            "time": tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
        })
        self.add_to_allevents(
            event_type='loan_settlement',
            paid_in_profit_currency=amount * rate_in_profit_currency + total_fee_in_profit_currency,
            paid_asset=asset,
            paid_in_asset=amount,
            received_asset='None',
            received_in_asset=0,
            received_in_profit_currency=0,
            timestamp=timestamp,
        )

    def add_loan_profit(
            self,
            gained_asset,
            gained_amount,
            gain_in_profit_currency,
            lent_amount,
            open_time,
            close_time,
    ):
        if not self.create_csv:
            return

        self.loan_profits_csv.append({
            'open_time': tsToDate(open_time, formatstr='%d/%m/%Y %H:%M:%S'),
            'close_time': tsToDate(close_time, formatstr='%d/%m/%Y %H:%M:%S'),
            'gained_asset': gained_asset,
            'gained_amount': gained_amount,
            'lent_amount': lent_amount,
            'profit_in_{}'.format(self.profit_currency): gain_in_profit_currency
        })
        self.add_to_allevents(
            event_type='interest_rate_payment',
            paid_in_profit_currency=0,
            paid_asset='None',
            paid_in_asset=0,
            received_asset=gained_asset,
            received_in_asset=gained_amount,
            received_in_profit_currency=gain_in_profit_currency,
            timestamp=close_time,
        )

    def add_margin_position(
            self,
            margin_notes,
            gained_asset,
            net_gain_amount,
            gain_in_profit_currency,
            timestamp,
    ):
        if not self.create_csv:
            return

        self.margin_positions_csv.append({
            'name': margin_notes,
            'time': tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'gained_asset': gained_asset,
            'gained_amount': net_gain_amount,
            'profit_in_{}'.format(self.profit_currency): gain_in_profit_currency
        })
        self.add_to_allevents(
            event_type='margin_position_close',
            paid_in_profit_currency=0,
            paid_asset='None',
            paid_in_asset=0,
            received_asset=gained_asset,
            received_in_asset=net_gain_amount,
            received_in_profit_currency=gain_in_profit_currency,
            timestamp=timestamp,
        )

    def add_asset_movement(
            self,
            exchange,
            category,
            asset,
            fee,
            rate,
            timestamp,
    ):
        if not self.create_csv:
            return

        self.asset_movements_csv.append({
            'time': tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'exchange': exchange,
            'type': category,
            'moving_asset': asset,
            'fee_in_asset': fee,
            'fee_in_{}'.format(self.profit_currency): fee * rate,
        })
        self.add_to_allevents(
            event_type='asset_movement_fee',
            paid_in_profit_currency=fee * rate,
            paid_asset=asset,
            paid_in_asset=fee,
            received_asset='None',
            received_in_asset=0,
            received_in_profit_currency=0,
            timestamp=timestamp,
        )

    def add_tx_gas_cost(
            self,
            transaction_hash,
            eth_burned_as_gas,
            rate,
            timestamp,
    ):
        if not self.create_csv:
            return

        self.tx_gas_costs_csv.append({
            'time': tsToDate(timestamp, formatstr='%d/%m/%Y %H:%M:%S'),
            'transaction_hash': transaction_hash,
            'eth_burned_as_gas': eth_burned_as_gas,
            'cost_in_{}'.format(self.profit_currency): eth_burned_as_gas * rate,
        })
        self.add_to_allevents(
            event_type='tx_gas_cost',
            paid_in_profit_currency=eth_burned_as_gas * rate,
            paid_asset='ETH',
            paid_in_asset=eth_burned_as_gas,
            received_asset='None',
            received_in_asset=0,
            received_in_profit_currency=0,
            timestamp=timestamp,
        )

    def create_files(self, out_dir='/home/lefteris/.rotkelchen/CSV/'):
        if not self.create_csv:
            return

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        self.dict_to_csv_file(os.path.join(out_dir, 'trades.csv'), self.trades_csv)
        self.dict_to_csv_file(os.path.join(out_dir, 'loan_profits.csv'), self.loan_profits_csv)
        self.dict_to_csv_file(
            os.path.join(out_dir, 'asset_movements.csv'),
            self.asset_movements_csv
        )
        self.dict_to_csv_file(os.path.join(out_dir, 'tx_gas_costs.csv'), self.tx_gas_costs_csv)
        self.dict_to_csv_file(
            os.path.join(out_dir, 'margin_positions.csv'),
            self.margin_positions_csv
        )
        self.dict_to_csv_file(
            os.path.join(out_dir, 'loan_settlements.csv'),
            self.loan_settlements_csv
        )
        self.dict_to_csv_file(os.path.join(out_dir, 'all_events.csv'), self.all_events_csv)