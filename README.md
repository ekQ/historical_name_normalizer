# Normalization tool for historical Finnish/Swedish names
Normalizes person and disease names in historical documents for record linkage. The tool is designed for Finnish / Swedish names.

## Dependencies
This tool requires the jellyfish library which can be installed via pip.
```
pip install jellyfish
```

## Usage
First create a `NameNormalizer` object for the name type you want to normalize and then call the `normalize()` method. Currently, the available name types are: `'first'` (given names), `'last'` (family names), `'patronym'`, and `'cause_of_death'`.

Example:
```
first_name_normalizer = NameNormalizer('first')
print first_name_normalizer.normalize(u'Hindrich')
```
which outputs
```
henrik
```

For more details, see file: name_normalizer.py

## Data
The name mappings are based on manually curated clusters of names referring to the same entity. These mappings have been obtained from the [Genealogical Society of Finland](http://www.genealogia.fi/index.php?language_id=1&p=226) and they are used by the [HisKi](http://hiski.genealogia.fi/hiski?en) program.

Each name mapping file, available under the data directory, contains the following columns:
1. Name variation
2. Normalized name
3. Popularity of the name variation in HisKi data
4. Popularity of all the names under the same normalized name in HisKi data
