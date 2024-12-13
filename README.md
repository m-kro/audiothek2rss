# License
This work is licensed under the MIT license.

# Example usage

## Search by category ID

Create RSS files with the latest episodes of the programs contained in the categories `42914736` (Kultur) and `42914742` (Wissen) 
and an overview website in the folder `out`.

```
python audiothek2rss.py --category-id 42914736 42914742 --directory out --html
```

## Search by category title

Same as before but without knowing the category ID, just the category title (or a part of the category title). This will return programs 
from all categories matching one of the search terms indicated by `--category-search`.

```
python audiothek2rss.py --category-search "Kultur" --directory out --html
```

## Query by program ID

If you know in advance which programs you want to create RSS files of, you can simply provide the program IDs. Only the programs with these IDs will be returned.

```
python audiothek2rss.py --program-id 13990287 13989277 --directory out --html
```

## Query by program title

If you don't recall the exact title of the program, you can search by keyword. Only one is allowed and will get added wildcards at begin and end.

```
python audiothek2rss.py --program-search "Presse" --directory out --html
```

You can restrict the search further by combining it with one of the category options:

```
python audiothek2rss.py --program-search "Presse" --category-search "Poltik & Hintergrund" --directory out --html
```

# Options

- **--category-id** : Audiothek category ID to restrict the found programs to the referenced categories
- **--category-search** : Restrict the found programs to those from categories with titles matching the search keyword
- **--program-id** : List of program IDs to query (overrides all other program and category restrictions)
- **--program-search** : Restrict the found programs to those with titles matching the search keyword
- **--max-programs** : Return at most this number of RSS files
- **--pagination** : Limit return size of API queries to this number of programs
- **--latest** : Query at most this number of episodes of each program (sorted by descending publication date)
- **--html** : Create the overview webpage
- **--directory** : Output directory to write to
- **--output** : Template of RSS file name, should contain `%d` to fill in the program ID


# Output

Two directories are created within the output directory:
 - rss : contains the RSS files
 - html : contains the overview webpage
 
 # Other
 
 The HTML template has been adapted from an original created by [TEMPLATED](http://templated.co).