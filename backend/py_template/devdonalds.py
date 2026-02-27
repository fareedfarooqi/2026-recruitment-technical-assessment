from dataclasses import dataclass
from typing import List, Union
from flask import Flask, request, jsonify
import re

# ==== Type Definitions, feel free to add or modify ===========================
@dataclass
class CookbookEntry:
	type: str

@dataclass
class RequiredItem():
	name: str
	quantity: int

@dataclass
class Recipe(CookbookEntry):
	type: str
	name: str
	required_items: List[RequiredItem]

@dataclass
class Ingredient(CookbookEntry):
	type: str
	name: str
	cook_time: int

# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
cookbook = []

# Task 1 helper (don't touch)
@app.route("/parse", methods=['POST'])
def parse():
	payload = request.get_json()
	raw_recipe_name = payload.get('input', '')
	parsed_name = parse_handwriting(raw_recipe_name)
	if parsed_name is None:
		return 'Invalid recipe name', 400
	return jsonify({'msg': parsed_name}), 200

# [TASK 1] ====================================================================
# Takes in a recipeName and returns it in a form that 
def parse_handwriting(raw_recipe_name: str) -> Union[str | None]:
	"""
	This function is used to clean up poorly formatted food names by removing unwanted characters and bad formatting.

	The function will:
		- Replace whitespaces, udnerscores or hypens (if they appear one or more times) with a single whitespace.
		- Remove any and all characters that are not letters ('A-Z' or 'a-z') or a single space character with no spaces.
		- Capitalise the first letter of every word in the recipe name.
		- Return the updated food name given that it's length is greater than 0. Otherwise it will return 'None'.
	"""
	cleaned_name = re.sub(r'[\s_-]+', " ", raw_recipe_name)
	cleaned_name = re.sub(r'[^A-Za-z ]+', "", cleaned_name)
	cleaned_name = cleaned_name.title().strip()

	return cleaned_name if len(cleaned_name) > 0 else None

# [TASK 2] ====================================================================
# Endpoint that adds a CookbookEntry to your magical cookbook
@app.route('/entry', methods=['POST'])
def create_entry():
	"""
	This function is used to create an entry for a recipe or ingredient into our cookbook.
	"""
	# WE must grab the JSON body from the request
	payload = request.get_json()

	if 'type' not in payload:
		return jsonify({"error": "The type is missing! Please add the type to your request!!!"}), 400
	elif payload['type'] not in ['recipe', 'ingredient']:
		return jsonify({"error": "Please use the specified type of either 'recipe' or 'ingredient'."}), 400

	if payload['type'] == "recipe" and "requiredItems" not in payload:
		return jsonify({"error": "Please ensure your recipe has a requiredItems field."}), 400

	if payload['type'] == "ingredient" and payload['cookTime'] < 0:
		return jsonify({"error": "Please enter a valid 'cookTime' that is greater or equal to 0!!!"}), 400

	for existing_entry in cookbook:
		if existing_entry.name == payload["name"]:
			return jsonify({"error": "An entry of this name already exists. Please provide unique entry names!!!"}), 400

	required_items_list = []
	if payload['type'] == "recipe":
		for required_item in payload["requiredItems"]:
			required_items_list.append(
				RequiredItem(
					name=required_item["name"],
					quantity=int(required_item["quantity"])
				)
			)

	if validate_required_items(required_items_list):
		return jsonify({"error": "There are duplicate entires in 'requiredItems'. It can only contain unique elements!!!"}), 400

	if payload['type'] == "recipe":
		cookbook.append(
			Recipe(
				type=payload["type"],
				name=payload["name"],
				required_items=required_items_list
			)
		)

	if payload['type'] == "ingredient":
		cookbook.append(
			Ingredient(
				type=payload["type"],
				name=payload["name"],
				cook_time=int(payload["cookTime"])
			)
		)

	return ("", 200)

def validate_required_items(required_items_list):
	"""
	This is a helper function that checks to see if an item with the same name is part of the 'requiredItems' field from our JSON data.
	"""
	seen = set()

	for item in required_items_list:
		if item.name in seen:
			return True
		seen.add(item.name)

	return False

# [TASK 3] ====================================================================
# Endpoint that returns a summary of a recipe that corresponds to a query name
@app.route('/summary', methods=['GET'])
def summary():
	"""
	This function provides a summary about the recipe that is to be cooked. It includes the name, total time taken to cook the recipe and the ingredients needed.
	"""
	query_name = request.args.get("name")

	recipe_entry = None
	for cookbook_item in cookbook:
		if cookbook_item.name == query_name and cookbook_item.type == 'recipe':
			recipe_entry = cookbook_item
		elif cookbook_item.name == query_name and cookbook_item.type == 'ingredient':
			return jsonify({"error": "An ingredient was passed in. Please ONLY pass in a valid recipe!!!"}), 400

	if recipe_entry is None:
		return jsonify({"error": "Recipe is not in the cookbook!!!"}), 400

	try:
		# We recrusively expand recipes until we reach base ingredients
		base_ingredients_dict = get_base_ingredients(recipe_entry)
	except Exception as e:
		return jsonify({"error": str(e)}), 400

	total_cook_time = get_total_cook_time(base_ingredients_dict)

	return {
		"name": query_name,
		"cookTime": total_cook_time,
		"ingredients": base_ingredients_dict
	}, 200

def get_base_ingredients(recipe, multiplier=1):
	"""
	This is a helper recursive function that allows us to get the base ingredients from a recipe that is to be cooked. I've made it recursive because a
	recipe can include a recipe which can include a recipe etc (like the "Skibidi Spaghetti" example from the spec. It was made up of a "Meatball" recipe.).
	As such we need to recursively expand our recipe in order to get the base ingredients and then we simply return those ingredients with their respective quantities.
	"""
	base_ingredients = {}

	for required_item in recipe.required_items:
		entry = None
		for cookbook_item in cookbook:
			if cookbook_item.name == required_item.name:
				entry = cookbook_item
				break

		if entry is None:
			raise Exception("The recipe contains recipes or ingredients that aren't in the cookbook.")

		total_quantity = required_item.quantity * multiplier

		if entry.type == "ingredient":
			base_ingredients[required_item.name] = base_ingredients.get(required_item.name, 0) + total_quantity
		elif entry.type == "recipe":
			sub_ingredients = get_base_ingredients(entry, multiplier=total_quantity)
			for ingredient_name, ingredient_quantity in sub_ingredients.items():
				base_ingredients[ingredient_name] = base_ingredients.get(ingredient_name, 0) + ingredient_quantity

	return base_ingredients

def get_total_cook_time(base_ingredients):
	"""
	This function simply computes the total cook time of the recipe given the list of base ingredients needed to make the recipe itself.
	"""
	total_cook_time = 0

	for ingredient_name, quantity in base_ingredients.items():
		for cookbook_item in cookbook:
			if cookbook_item.name == ingredient_name:
				total_cook_time += cookbook_item.cook_time * quantity

	return total_cook_time

# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, port=8080)