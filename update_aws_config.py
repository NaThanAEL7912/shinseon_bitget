import json

path = '/home/ubuntu/server_config.json'
with open(path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['BITGET_API_KEY'] = 'bg_014c0d0b0abfb5adf095bb22e77ed943'
config['BITGET_SECRET_KEY'] = 'a4850c915945b03109e6418582a3023b0c072703839e57fac758246c42ffbd84'
config['BITGET_PASSPHRASE'] = '7912271923114'

with open(path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
print('Config updated successfully.')
