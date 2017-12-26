# See readme.md for instructions on running this code.

from typing import Any
import requests

class BaremetricsHandler(object):
    def initialize(self, bot_handler: Any) -> None:
        self.config_info = bot_handler.get_config_info('baremetrics')
        self.api_key = self.config_info['api_key']

        self.auth_header = {
            'Authorization': 'Bearer ' + self.api_key
        }

        self.commands = ['help', 'list-commands', 'account-info', 'list-sources', 'list-plans <source_id>',
                         'list-customers <source_id>',
                         'list-subscriptions <source_id>']

        self.descriptions = ['Display bot info', 'Display the list of available commands', 'Display the account info',
                             'List the sources', 'List the plans for the source', 'List the customers in the source',
                             'List the subscriptions in the source']

    def usage(self) -> str:
        return '''
        This bot gives updates about customer behavior, financial performance, and analytics
        for an organization using the Baremetrics Api.\n
        Enter `list-commands` to show the list of available commands.
        Version 1.0
        '''

    def handle_message(self, message: Any, bot_handler: Any) -> None:
        message['content'] = message['content'].strip()

        if message['content'].lower() == 'help':
            bot_handler.send_reply(message, self.usage())
            return

        if message['content'].lower() == 'list-commands':
            response = '**Available Commands:** \n'
            for command, description in zip(self.commands, self.descriptions):
                response += ' - {} : {}\n'.format(command, description)

            bot_handler.send_reply(message, response)
            return

        if message['content'] == '':
            bot_handler.send_reply(message, 'No Command Specified')
            return

        response = self.generate_response(message['content'])
        bot_handler.send_reply(message, response)

    def generate_response(self, command: str) -> str:
        command = command.lower()

        if command == 'account-info':
            return self.get_account_info()

        if command == 'list-sources':
            return self.get_sources()

        part_commands = command.split()

        try:
            if part_commands[0] == 'list-plans':
                return self.get_plans(part_commands[1])

            if part_commands[0] == 'list-customers':
                return self.get_customers(part_commands[1])

            if part_commands[0] == 'list-subscriptions':
                return self.get_subscriptions(part_commands[1])

        except IndexError:
            return 'Missing Params.'

        return 'Invalid Command.'

    def get_account_info(self) -> str:
        url = "https://api.baremetrics.com/v1/account"
        account_response = requests.get(url, headers=self.auth_header)

        account_data = account_response.json()
        account_data = account_data['account']

        response = '**Your account information:** \n'
        response += 'Id: {id}\n'.format(id=account_data['id'])
        response += 'Company: {company}\n'.format(company=account_data['company'])
        response += 'Default Currency: {currency_name}'.format(currency_name=account_data['default_currency']['name'])

        return response

    def get_sources(self) -> str:
        url = 'https://api.baremetrics.com/v1/sources'
        sources_response = requests.get(url, headers=self.auth_header)

        sources_data = sources_response.json()
        sources_data = sources_data['sources']

        response = '**Listing sources:** \n'
        for index, source in enumerate(sources_data):
            response += '{}.ID: {}\nProvider: {}\nProvider ID: {}\n\n'.format(index + 1, source['id'],
                                                                              source['provider'],
                                                                              source['provider_id'])

        return response

    def get_plans(self, source_id: str) -> str:
        url = 'https://api.baremetrics.com/v1/{}/plans'.format(source_id)
        plans_response = requests.get(url, headers=self.auth_header)

        plans_data = plans_response.json()
        plans_data = plans_data['plans']

        response = '**Listing plans:** \n'
        for index, plan in enumerate(plans_data):
            response += '{}.Name: {}\nActive: {}\nInterval: {}\nInterval Count: {}\nAmounts: \n' \
                .format(index + 1, plan['name'], plan['active'], plan['interval'], plan['interval_count'])

            for amount in plan['amounts']:
                response += ' - {} {}\n'.format(amount['amount'], amount['currency'])

            response += '\n\n'

        return response

    def get_customers(self, source_id: str) -> str:
        url = 'https://api.baremetrics.com/v1/{}/customers'.format(source_id)
        customers_response = requests.get(url, headers=self.auth_header)

        customers_data = customers_response.json()
        customers_data = customers_data['customers']

        response = '**Listing customers:** \n'
        for index, customer in enumerate(customers_data):
            response += '{}.Name: {}\nDisplay Name: {}\nOID: {}\nActive: {}\nEmail: {}\nNotes: {}\nCurrent Plans: \n' \
                .format(index + 1, customer['display_name'], customer['name'], customer['oid'], customer['is_active'],
                        customer['email'],
                        customer['notes'])

            for plan in customer['current_plans']:
                response += ' - {}\n'.format(plan['name'])

            response += '\n\n'

        return response

    def get_subscriptions(self, source_id: str) -> str:
        url = 'https://api.baremetrics.com/v1/{}/subscriptions'.format(source_id)
        subscriptions_response = requests.get(url, headers=self.auth_header)

        subscriptions_data = subscriptions_response.json()
        subscriptions_data = subscriptions_data['subscriptions']

        response = '**Listing subscriptions:** \n'
        for index, subscription in enumerate(subscriptions_data):
            response += '{}.Customer Name: {}\nCustomer Display Name: {}\nCustomer OID: {}\nCustomer Email: {}\n' \
                        'Active: {}\nPlan Name: {}\nPlan Amounts: \n' \
                .format(index + 1, subscription['customer']['name'], subscription['customer']['display_name'],
                        subscription['customer']['oid'], subscription['customer']['email'], subscription['active'],
                        subscription['plan']['name'])

            for amount in subscription['plan']['amounts']:
                response += ' - {} {}\n'.format(amount['amount'], amount['symbol'])

            response += '\n\n'

        return response

handler_class = BaremetricsHandler
