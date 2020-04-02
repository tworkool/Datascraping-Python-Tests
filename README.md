
This script searches for words on a website which has  `<article>` tags. This applies to almost all newspaper websites. To add or remove websites and words to be searched for, modify the settings.json file

**settings.json**

```json
{
    	"search_terms" : [
    		"word1",
    		"word2"
	],
    	"search_sites" : [  
	    	 {  
		    	"url": "https://www.newspaper_mainpage.de/",  
	    		"name": "newspaper_name"
	    	 },  
    	]
    }
```
The search_terms list should all be lowercase, otherwise now words will be found.
Words and websites can be added anytime.
The name can also be left out. Then the main page name will be taken as name (in this case: newspaper_mainpage)

The script prevents you from updating more than once within 3 hours from your last update
