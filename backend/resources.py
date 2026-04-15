import json


def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

with open('./data/linkedin.md', 'r') as file:
    linkedin = file.read()

with open('./data/summary.md', 'r') as file:
    summary = file.read()

with open('./data/style.txt', 'r') as file:
    style = file.read()

facts = load_json('./data/facts.json')
