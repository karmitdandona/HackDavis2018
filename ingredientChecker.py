import json

from pprint import pprint

def main(allergens):
	#allergens = ["almonds", "flour", "peanuts", "sugar", "cacao"] 
	result = checkIngredients(allergens, 'input.json')

	if len(result) == 0:
		print("No problem")

	return result

def checkIngredients(allergens, filename):

	results = {} 	#dictionary containing matches

	with open(filename, 'r') as f:
		datastore = json.load(f)
		textArray = datastore["textAnnotations"]
		firstDict = textArray[0]
		text = firstDict["description"]
		lowerText = text.lower()
	# extracting entire string of text interpreted by API in json

	for badIngredients in allergens:
		if badIngredients in lowerText:
			results[badIngredients] = True

	for badIngredients in allergens:
		if not badIngredients in results:
			results[badIngredients] = False
	#for to append all the negative ingredients (not found)

	return results


main()
