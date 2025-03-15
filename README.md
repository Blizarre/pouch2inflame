**Note:** *This project has been archived as I have moved on from the kindle ecosystem. I am now using the fabulous [koreader](https://github.com/koreader/koreader) with the [wallabag](https://wallabag.org/) integration.*

# Pouch2Inflame

Script and docker container to automatically send [pocket](https://www.getpocket.com) links to your [kindle](https://www.amazon.com/kindle/) by email.

Very similar to a popular project that I used for a long time and that has such a perfect and obvious name that i couldn't find anything better. I then used a Thesaurus to find synonyms and create the name of this project.


## Goals

One of the goal of that project was to keep the installation simple and lightweight:
- One python3 script without any dependencies. It's been a bit of a challenge, given that the libraries included with Python are fairly low-level. But I have been able to send emails with attachments, make https requests and load `toml` config fairly easily. I have not been able to implement updating the toml in place (for `get_token`) as that is not supported.
- Simple config file in a file format that has comments (see `config.toml.template`)
- Use of docker containers to isolate the converter apps as a weak isolation and security measure. Each app will run isolated and only communicate with the outside via stdin/stdout/network. It's not enough for a public service, but the proper solution would be out of the scope of this one day project.


## Workflow

1. `main.py` fetch non-archived articles from each user ([getpocket.com API](https://getpocket.com/developer/))
2. `main.py` Spawn `extractor` in a docker container, a small wrapper cli around the [readibility](https://github.com/mozilla/readability) library to extract the content of the article from the page
3. The output of `extractor` is fed to [pandoc](https://pandoc.org), also run inside a docker container. `Pandoc` will convert the html into epub and stream it to stdout
4. `main.py` will write the epub to a file and send it to the kindle email address stored in the config for the current user
5. `main.py` will then archive the article in pocket using the [modify API](https://getpocket.com/developer/docs/v3/modify#action_archive)

## How to use

1. Get a consumer_key from Pocket at https://getpocket.com/developer/apps/
2. Get your kindle address from the amazon website
3. Create and update the config file with these information
```
cp config.toml.template config.toml
# Edit the fields inside the configuration file
```
4. Build the docker container containing the conversion pipeline
```
make docker_build
```
5. Get a token for your user. You will have to authenticate to pocket
```
python  main.py get_token
```
6. Update the accounts.USER_NAME entry with your name, token, and kindle address
7. Run main.py every time you want to fetch and send the articles(use a crontab)
```
python  main.py process_and_send
```
