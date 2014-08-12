{{header}}Functionality available for '{{plugin.name}}':{{endc}}
{{!----------------------------}}
{{#plugin.plugins_can_enumerate}}
    - Enumerate plugins {{blue}}({{plugin.plugins_wordlist_size}} plugins{{#plugin.plugins_mtime}}, last updated {{plugin.plugins_mtime}}{{/plugin.plugins_mtime}}){{endc}}
{{/plugin.plugins_can_enumerate}}
{{!----------------------------}}
{{#plugin.themes_can_enumerate}}
    - Enumerate themes {{blue}}({{plugin.themes_wordlist_size}} themes{{#plugin.themes_mtime}}, last updated {{plugin.themes_mtime}}{{/plugin.themes_mtime}}){{endc}}
{{/plugin.themes_can_enumerate}}
{{!----------------------------}}
{{#plugin.interesting_can_enumerate}}
    - Enumerate interesting urls {{blue}}({{plugin.interesting_url_size}} urls){{endc}}
{{/plugin.interesting_can_enumerate}}
{{!----------------------------}}
{{#plugin.version_can_enumerate}}
    - Enumerate version {{blue}}(up to version {{plugin.version_highest}}){{endc}}
{{/plugin.version_can_enumerate}}
