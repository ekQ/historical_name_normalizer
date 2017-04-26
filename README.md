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
