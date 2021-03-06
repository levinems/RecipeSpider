import re
from six.moves.urllib.parse import urlparse, urljoin, urlsplit, SplitResult
from six.moves.urllib.request import urlopen, Request
import requests
from bs4 import BeautifulSoup
import sys
import MySQLdb
from scrapme import getProxy
from fake_useragent import UserAgent
import time
import json
import datetime
from stdsitelib import imagegrabber, hdr

#this will be used for an automated spider
sites = ['https://pinchofyum.com', 'http://rachlmansfield.com','https://www.101cookbooks.com','http://12tomatoes.com','http://allrecipes.com','https://www.americastestkitchen.com','https://www.bbc.co.uk/food/recipes/']
sites.extend(['https://www.bbcgoodfood.com','https://www.bhg.com','https://www.bigoven.com','https://www.bonappetit.com','https://www.chowhound.com','http://www.cookingchanneltv.com','https://cooking.nytimes.com'])
sites.extend(['http://www.cooks.com','https://www.cooksillustrated.com','https://www.dadcooksdinner.com','http://www.eatingwell.com','https://elanaspantry.com','https://www.epicurious.com'])
sites.extend(['https://food52.com','http://www.foodandwine.com','http://www.geniuskitchen.com','http://www.foodnetwork.com','http://www.foodnetwork.co.uk'])

#sites to pull from the print option as this should make the scraping faster
printSiteList = ['rachlmansfield.com']

#sites either without a print option or poorly formated print pages
noPrintSiteList = ['allrecipes.com','pinchofyum.com','www.101cookbooks.com','12tomatoes.com','www.americastestkitchen.com','www.bbc.co.uk','www.bbcgoodfood.com','www.bigoven.com']
noPrintSiteList.extend(['www.bigoven.com','www.bonappetit.com','www.chowhound.com','www.cookingchanneltv.com','cooking.nytimes.com','www.cooks.com','www.cooksillustrated.com'])
noPrintSiteList.extend(['www.dadcooksdinner.com','www.eatingwell.com','elanaspantry.com','www.epicurious.com','food52.com','www.foodandwine.com','www.geniuskitchen.com'])
noPrintSiteList.extend(['www.foodnetwork.com','www.foodnetwork.co.uk','www.bhg.com'])

#database connection
db = MySQLdb.connect(host="localhost", user="recipelibrarian", passwd="cheftobe", db="recipelibrarian", charset='utf8', use_unicode=True)
cursor = db.cursor()

#get a proxy so I don't get blocked from spidering web sites (it has happened already)
proxy = getProxy()

def preSeed(url):
    cur = db.cursor()
    cur.execute("select link from recipes where link like %s", ("%" + url + "%",))
    seed = set()
    for row in cur.fetchall():
        seed.add(row[0])
    return seed

#this function is to make sure we don't have duplicates in the datbase
def urlValidate(url):
    cur = db.cursor()
    cur.execute("select count(*) from recipes where link=%s", [url])
    for row in cur.fetchall():
        count = row[0]
    return count


def linktempAdd(link):
    cur = db.cursor()
    add_link = "insert into linkstemp (link) values (%s)"
    cur.execute(add_link, (link,))
    db.commit()

def checkTemp(url):
    cur = db.cursor()
    cur.execute("select count(*) from linkstemp where link=%s", [url])
    for row in cur.fetchall():
        count = row[0]
    return count


def dumpLinksTemp():
    cur = db.cursor()
    cur.execute("TRUNCATE `recipelibrarian`.`linkstemp`")
    db.commit()

def getSiteID(domain):
    cur = db.cursor()
    domain = domain.replace("www.","")
    cur.execute("select id from recipesites where domain=%s", [domain])
    for row in cur.fetchall():
        id = row[0]
    return id


#this is for scraping all content
def contentScraper(url, domain):
    siteid = getSiteID(domain)

    response = ''
    while response == '':
        try:
            #pull the page data
            response = requests.get(url, headers=hdr, proxies=proxy)
            #put it in BS
            soup = BeautifulSoup(response.content, "lxml")
        except:
            print("Connection refused by the server..")
            print("Let me sleep for 5 seconds")
            print("ZZzzzz...")
            time.sleep(5)
            print("Was a nice sleep, now let me continue...")
            continue
# pinch of yum
    if "pinchofyum" in url:
        try:
            # json and html scraping since the instructions are not in the json
            for recipe in soup.find_all('script', type='application/ld+json'):
                # find the json data for the recipe since this site uses multiple json scripts
                if '\"@type\": \"Recipe\"' in  recipe.text:
                    rawdata = recipe.text
                    data = json.loads(recipe.text)
                    #print(data['@type'])
                    # title
                    title = data['name']
                    #noticed an error in their json
                    title = title.replace("<span class=\"fn\">","")
                    #print(title)
                    # link
                    link = data["url"]
                    #print(link)
                    # image link
                    imglink = data['image']['url']
                    imgblob = imagegrabber(imglink)
                    #print(imglink)
                    # description
                    descr = data['description']
                    #print(descr)
                    # date published
                    d = soup.find('meta', property='article:published_time')
                    d = d["content"]
                    datePosted = d.replace("T", " ")[:-6]
                    #print(datePosted)
                    # ingredients loop through the ingredient list
                    ing = ""
                    ingList = data['recipeIngredient']
                    i = 0
                    while i < len(ingList):
                        ing += ingList[i] + "\n"
                        i += 1
                    #print(ing)
                    # instructions
                    instrList = data['recipeInstructions']
                    i = 0
                    instr = ""
                    while i < len(instrList):
                        instr += instrList[i] + "\n"
                        i += 1
                    #print(instr)
                    if urlValidate(link) == 0:
                        if ing:
                            print("title:%s" % title)  # print title
                            print("Date published %s" % datePosted)
                            print("Url: %s" % link)
                            print("Description: %s" % descr)
                            print("imglink: %s" % imglink)  # print image source
                            print("ingredients: %s" % ing)  # print ingredients
                            print("instructions: %s" % instr)
                            add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                            cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                            db.commit()

                    else:
                        print("link in database")

        except:
            print("no recipe found @ %s" % url)
#all recipes
    if "allrecipes" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find("meta", property="og:url")
            link = link["content"]
            #print(link)
            # description
            descr = soup.find("meta", property="og:description")
            descr = descr["content"]
            #print(descr)
            # date
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(img)
            # ingredients
            ing = ""
            for ingtxt in soup.find_all('span', itemprop="ingredients"):
                ing += ingtxt.text + "\n"

            #print(ing)
            # instructions
            instr = ""
            for insttxt in soup.find_all('span', {"class": "recipe-directions__list--item"}):
                instr += insttxt.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print(img)  # print image source
                    print(ing)  # print ingredients
                    print(instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, instr, imgblob, siteid))
                    db.commit()
        except:
           print("no recipe found @ %s" % url)

#rachelmansfield
    if "rachlmansfield" in url:
        try:
            # title
            title = soup.find('div', itemprop='name')
            title = title.get_text()
            #print(title)
            # link
            link = soup.find('div', {'class': 'ERPTagline'})
            linktxt = link.get_text()
            linktxt = linktxt.replace("rachLmansfield","")
            linktxt = linktxt.replace("Recipe by","")
            linktxt = linktxt.replace("at","")
            link = linktxt.strip()
            #print(link)
            # description contains no description on print page so we'll use the title which is pretty descriptive
            descr = title
            # date no date
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # image link
            img = soup.find('link', itemprop='image')
            imglink = img["href"]
            imgblob = imagegrabber(imglink)
            #print(img["href"])
            # ingredients
            ingdiv = soup.find('div', {'class': 'ERSIngredients'})
            ing = ""
            for litag in ingdiv.find_all('li', class_='ingredient'):
                # prints the p tag content
                ing=ing + litag.text + "\n"
            #print(ing)
            # instructions
            instrdiv = soup.find('div', {'class': 'ERSInstructions'})
            instr = ""
            for litag in instrdiv.find_all('li', class_='instruction'):
                # prints the p tag content
                instr = instr + litag.text + "\n"
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % img)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ing, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, img, datePosted, instr, imgblob, siteid))
                    db.commit()
        except:
            print("no recipe found @ %s" % url)

#101cookbooks.com
    if "101cookbooks" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            # description
            descr = soup.find('meta', {"name":"description"})
            descr = descr["content"]
            #print(descr)
            # date no date
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # ingredients
            ingdiv = soup.find('div', id="recipe")
            ing = ""
            #containted in blockquote in recipe div
            for bq in ingdiv.find_all('blockquote'):
                # prints the p tag content
                ing = ing + bq.text + "\n"
            #print(ing)
            # instructions are in the same div as the ingredients but not in the blockquote
            instr = ""
            for p in ingdiv.find_all('p'):
                # prints the p tag content
                instr = instr + p.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#12tomatoes.com
    if "12tomatoes" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            # description
            descr = soup.find('meta', {"name":"description"})
            descr = descr["content"]
            #print(descr)
            # date
            d = soup.find('meta', property='article:published_time')
            datePosted = d["content"]
            datePosted = datePosted.replace("T"," ")
            datePosted = datePosted[:-6]
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # ingredients
            ingdiv = soup.find('div', id="recipe-ingredients")
            ing = ""
            #containted in blockquote in recipe div
            for li in ingdiv.find_all('li'):
                # prints the p tag content
                ing = ing + li.text + "\n"
            #print(ing)
            # instructions are in the same div as the ingredients but not in the blockquote
            instr = ""
            instrdiv = soup.find('div', id="recipe-prep")
            for li in instrdiv.find_all('li'):
                # prints the p tag content
                instr = instr + li.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#allrecipes.com
    if "allrecipes" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)

            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)

            # description
            descr = soup.find('div', {"class":"recipe-print__description"})
            descr = descr.text
            #print(descr)
            # date no date
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # image link

            img = soup.find('img', {'class':'recipe-print__recipe-img'})
            imglink = img["src"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # ingredients
            ingdiv = soup.find('div', {"class":"recipe-print__container2"})
            ing = ""
            #containted in blockquote in recipe div
            for ul in ingdiv.find_all("ul"):
                for li in ul.find_all('li'):
                    # prints the p tag content
                    ing = ing + li.text.strip()
                    ing = ing + "\n"
            #print(ing)

            # instructions are in the same div as the ingredients but not in the blockquote
            instr = ""
            for ol in ingdiv.find_all("ol"):
                for li in ol.find_all("li"):
                    # prints the p tag content
                    instr = instr + li.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#www.americastestkitchen.com
#of course they want us to pay for a subscription and we should obey the google off tags but.....

    if "americastestkitchen" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = soup.find('meta', {"name":"description"})
            descr = descr["content"]
            #print(descr)
            # date no date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # ingredients
            ingdiv = soup.find('div', {"class":"recipe__ingredient"})
            ing = ""
            #containted in tables in recipe div
            #measurement and ingredient are in different cells
            for table in ingdiv.find_all('table'):
                for td in table.find_all('td'):
                    # prints the p tag content
                    ing = ing + td.text.strip()
                ing = ing + "\n"
            #print(ing)
            # instructions are in the same div as the ingredients but not in the blockquote
            instr = ""
            instrdiv = soup.find('div', {"class": "recipe__instructions--content blurred"})
            for p in instrdiv.find_all('p'):
                # prints the p tag content
                instr = instr + p.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#bbc.co.uk

    if "bbc.co.uk" in url:
        try:
            # title
            title = soup.find('h1', {"class": "content-title__text"})
            title = title.text
            #print(title)

            # link
            link = url
            #print(link)
            # image link
            img = soup.find('img', {'class':'recipe-media__image'})
            imglink = img["src"]
            imgblob = imagegrabber(imglink)
            #print(imglink)

            # description
            descr = soup.find('p', {"class":"recipe-description__text"})
            descr = descr.text
            #print(descr)

            # date no date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # ingredients
            ingdiv = soup.find('ul', {"class":"recipe-ingredients__list"})
            ing = ""
            #ingredients
            for li in ingdiv.find_all('li'):
                ing = ing + li.text + "\n"
            #print(ing)

            # instructions are in the same div as the ingredients but not in the blockquote
            instr = ""
            instrdiv = soup.find('ol', {"class": "recipe-method__list"})
            for li in instrdiv.find_all('li'):
                for p in li.find_all('p'):
                    # prints the p tag content
                    instr = instr + p.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#bbcgoodfood
    if "bbcgoodfood" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = soup.find('meta', property="og:description")
            descr = descr["content"]
            #print(descr)
            # date no date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # ingredients
            ing = ""
            # ingredients
            ingdiv = soup.find('ul', {"class": "ingredients-list__group"})
            for li in ingdiv.find_all('li'):
                ing = ing + li.text + "\n"
            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find('ol', {"class": "method__list"})
            for li in instrdiv.find_all('li'):
                for p in li.find_all('p'):
                    # prints the p tag content
                    instr = instr + p.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()
        except:
            print("no recipe found @ %s" % url)

#BHG.com Better Homes and Gardens
    if "bhg.com" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = soup.find('meta', property="og:description")
            descr = descr["content"]
            #print(descr)
            # date
            d = soup.find('meta', property='bt:pubDate')
            datePosted = d["content"].replace("T"," ")
            datePosted = datePosted[:-6]
            #print(datePosted)

            # ingredients
            ing = ""
            # ingredients
            ingdiv = soup.find('ul', {"class": "recipe__ingredientList"})
            for li in ingdiv.find_all('li'):
                for txt in li.find_all('span'):
                    ing = ing + txt.text + " "
                ing = ing + "\n"
            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find('ol', {"class": "recipe__directionsList"})
            for li in instrdiv.find_all('li'):
                instr = instr + li.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#bigoven.com
    if "bigoven.com" in url:
        try:
            rawdata = soup.find('script', type='application/ld+json').text
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = soup.find('meta', property="og:description")
            descr = descr["content"]
            #print(descr)
            # date no date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')

            # ingredients
            ing = ""
            # ingredients
            ingdiv = soup.find('textarea', id='recipe-textarea')
            ing = ingdiv.text
            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find('div', {"class": "recipe-instructions"})
            for p in instrdiv.find_all('p'):
                instr = instr + p.text.strip() + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#bonappetit.com
    if "bonappetit.com" in url:
        try:
            #json and html scraping since the instructions are not in the json
            rawdata = soup.find('script', type='application/ld+json').text
            data = json.loads(soup.find('script', type='application/ld+json').text)
            #title
            title = data['name']
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #image link
            imglink = data['image']
            imgblob = imagegrabber(imglink)
            #print(imglink)
            #description
            descr = data['description']
            #print(descr)
            #date published
            d = data['datePublished']
            datePosted = d.replace("T", " ")[:-10]

            #print(datePosted)
            #ingredients loop through the ingredient list
            ing = ""
            ingList = data['recipeIngredient']
            i = 0
            while i < len(ingList):
                ing += ingList[i] + "\n"
                i += 1
            #print(ing)
            #instructions
            instrdiv = soup.find("ul", {'class': 'steps'})
            instr = ""
            for li in instrdiv.find_all('li'):
                instr = instr + li.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#chowhound.com
    if "chowhound.com" in url:
       try:
            rawdata = soup.find('script', type='application/ld+json').text
            #json and html scraping since the instructions are not in the json
            data = json.loads(soup.find('script', type='application/ld+json').text)
            #title
            title = data['name']
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            #image link
            imglink = data['image']['url']
            imgblob = imagegrabber(imglink)
            #print(imglink)
            #description
            descr = data['description']
            #print(descr)
            #date published
            d = data['datePublished']
            #Dec 18, 2017 09:17 AM
            datePosted = datetime.datetime.strptime(d, "%b %d, %Y %I:%M %p").strftime("%Y-%m-%d %H:%M:%S")
            #print(datePosted)
            #ingredients loop through the ingredient list
            ing = ""
            ingList = data['recipeIngredient']
            i = 0
            while i < len(ingList):
                ing += ingList[i] + "\n"
                i += 1
            #print(ing)
            #instructions
            instr = data['recipeInstructions']
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

       except:
           print("no recipe found @ %s" % url)

#cookingchannel.com
    if "cookingchanneltv.com" in url:
       try:
            #json and html scraping since the instructions are not in the json
            rawdata = soup.find('script', type='application/ld+json').text
            data = json.loads(soup.find('script', type='application/ld+json').text)
            #title
            title = data['name']
            #print(title)
            # link
            link = data["url"]
            #print(link)
            #image link
            imglink = data['image']['url']
            imgblob = imagegrabber(imglink)
            #print(imglink)
            #description
            descr = data['description']
            #print(descr)
            #date published
            d = data['datePublished']
            datePosted = d.replace("T", " ")[:-10]
            #print(datePosted)
            #ingredients loop through the ingredient list
            ing = ""
            ingList = data['recipeIngredient']
            i = 0
            while i < len(ingList):
                ing += ingList[i] + "\n"
                i += 1
            #print(ing)
            #instructions
            instrList = data['recipeInstructions']
            i = 0
            instr = ""
            while i < len(instrList):
                instr += instrList[i] + "\n"
                i += 1
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

       except:
           print("no recipe found @ %s" % url)

#cooking.nytimes
    if "cooking.nytimes.com" in url:
        try:
            # title
            title = soup.find('meta', property='og:title')
            title = title["content"]
            #print(title)
            # link
            link = soup.find('meta', property='og:url')
            link = link["content"]
            #print(link)
            # image link
            img = soup.find('meta', property='og:image')
            imglink = img["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = soup.find('meta', property="og:description")
            descr = descr["content"]
            #print(descr)
            # date
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            #print(datePosted)

            # ingredients
            ing = ""
            # ingredients
            ingdiv = soup.find('ul', {"class": "recipe-ingredients"})
            for li in ingdiv.find_all('li'):
                for txt in li.find_all('span'):
                    ing += txt.text.strip() + " "
                ing += "\n"

            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find('ol', itemprop="recipeInstructions")
            for li in instrdiv.find_all('li'):
                instr = instr + li.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#cooks.com
    if "cooks.com" in url:
        try:
            # title
            title = soup.find("title").text
            #print(title)
            # link
            link = url
            #print(link)
            # image link
            img = soup.find('img', {"class": "photo"})
            imglink = img["src"]
            #print(imglink)
            # description no description for recipe?
            descr = title
            #print(descr)
            # date
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            #print(datePosted)

            # ingredients
            ing = ""
            # ingredients
            ingdiv = soup.find_all('span', {"class": "ingredient"})
            for txt in ingdiv:
                ing += txt.text
                ing += "\n"

            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find('div', {"class": "instructions"})
            for p in instrdiv.find_all('p'):
                instr = instr + p.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#cooksillustrated.com
    if "cooksillustrated.com" in url:
       try:
            #json and html scraping since the instructions are not in the json
            rawdata = soup.find('script', type='application/ld+json').text
            data = json.loads(soup.find('script', type='application/ld+json').text)
            #title
            title = data['name']
            #print(title)
            # link
            link = data["url"]
            #print(link)
            #image link
            imglink = data['image']
            imgblob = imagegrabber(imglink)
            #print(imglink)
            #description
            descr = data['description']
            #print(descr)
            #date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')

            #ingredients loop through the ingredient list
            ing = ""
            ingList = soup.find_all("table", {"class": "recipe__ingredient--list"})
            for tbl in ingList:
                for td in tbl.find_all("tr"):
                    for txt in td.find_all("td"):
                        ing += txt.text.strip() + " "
                ing = ing.strip() + "\n"
            #print(ing)

            #instructions
            instr = ""
            instrdiv = soup.find("div", {"class": "recipe__instructions"})
            for p in instrdiv.find_all("p"):
                instr += p.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

       except:
           print("no recipe found @ %s" % url)

#dadscookdinner
#https://www.dadcooksdinner.com/pressure-cooker-baby-back-ribs/
    if "dadcooksdinner.com" in url:
        try:

            for recipe in soup.find_all('script', type='application/ld+json'):
                data = json.loads(recipe.text)
                if "Recipe" in data['@type']:
                    rawdata = recipe.text
                    # title
                    title = data['name']
                    #print(title)
                    # link
                    link = data["url"]
                    #print(link)
                    #image link
                    imglink = data['image']['url']
                    imgblob = imagegrabber(imglink)
                    #print(imglink)
                    #description
                    descr = data['description']
                    #print(descr)
                    #date published
                    datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
                    # ingredients loop through the ingredient list
                    ing = ""
                    ingList = data['recipeIngredient']
                    i = 0
                    while i < len(ingList):
                        ing += ingList[i] + "\n"
                        i += 1
                    #print(ing)
                    # instructions
                    instrList = data['recipeInstructions']
                    i = 0
                    instr = ""
                    while i < len(instrList):
                        instr += instrList[i] + "\n"
                        i += 1
                    #print(instr)
                    if urlValidate(link) == 0:
                        if ing:
                            print("title:%s" % title)  # print title
                            print("Date published %s" % datePosted)
                            print("Url: %s" % link)
                            print("Description: %s" % descr)
                            print("imglink: %s" % imglink)  # print image source
                            print("ingredients: %s" % ing)  # print ingredients
                            print("instructions: %s" % instr)
                            add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                            cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                            db.commit()
        except:
            print("no recipe found @ %s" % url)
#eatingwell.com
    if "eatingwell.com" in url:
       try:
            #title
            title = soup.find("meta", property="og:title")
            title = title["content"]
            #print(title)
            # link
            link = soup.find("meta", property="og:url")
            link = link["content"]
            #print(link)
            #image link
            imglink = soup.find("meta", property="og:image")
            imglink = imglink["content"]
            #print(imglink)
            #description
            descr = soup.find("meta", property="og:description")
            descr = descr["content"]
            #print(descr)
            #date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')

            #ingredients loop through the ingredient list
            ing = ""
            ingList = soup.find_all("span", itemprop="ingredients")
            for span in ingList:
                ing += span.text + "\n"
            #print(ing)

            #instructions
            instr = ""
            instrdiv = soup.find("ol", itemprop="recipeInstructions")
            for span in instrdiv.find_all("span"):
                instr += span.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

       except:
           print("no recipe found @ %s" % url)
#elanaspantry.com
    if "elanaspantry.com" in url:
        try:
            # title
            title = soup.find("meta", property="og:title")
            title = title["content"]
            #print(title)
            # link
            link = soup.find("meta", property="og:url")
            link = link["content"]
            #print(link)
            # image link
            imglink = soup.find("meta", property="og:image")
            imglink = imglink["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = soup.find("meta", property="og:description")
            descr = descr["content"]
           # print(descr)
            # date published
            d = soup.find("meta", property="article:published_time")
            datePosted = d["content"].replace("T", " ")[:-6]
            #print(datePosted)

            # ingredients loop through the ingredient list
            ing = ""
            ingList = soup.find("ul", {"class": "wpurp-recipe-ingredients"})
            for li in ingList.find_all("li"):
                ing += li.text + "\n"
            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find("ol", {"class": "wpurp-recipe-instructions"})
            for li in instrdiv.find_all("li"):
                instr += li.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#www.epicurious.com
    if "epicurious.com" in url:
        try:
            # title
            title = soup.find("meta", property="og:title")
            title = title["content"]
            #print(title)
            # link
            link = soup.find("meta", property="og:url")
            link = link["content"]
            #print(link)

            # image link
            imglink = soup.find("meta", property="og:image")
            imglink = imglink["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)

            # description
            descr = soup.find("meta", property="og:description")
            descr = descr["content"]
            #print(descr)

            # date published
            d = soup.find("meta", itemprop="datePublished")
            datePosted = d["content"].replace("T", " ")[:-5]
            #print(datePosted)

            # ingredients loop through the ingredient list
            ing = ""
            ingList = soup.find("ul", {"class": "ingredients"})
            for li in ingList.find_all("li"):
                ing += li.text + "\n"
            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find("ol", {"class": "preparation-steps"})
            for li in instrdiv.find_all("li"):
                instr += li.text.strip() + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#food52.com
    if "food52.com" in url:
        try:
            # title
            title = soup.find("meta", property="og:title")
            title = title["content"]
            #print(title)
            # link
            link = soup.find("meta", property="og:url")
            link = link["content"]
            #print(link)

            # image link
            imglink = soup.find("meta", property="og:image")
            imglink = imglink["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)

            # description
            descr = soup.find("meta", property="og:description")
            descr = descr["content"]
            #print(descr)

            # date published
            d = soup.find("meta", {"name": "sailthru.date"})
            datePosted = d["content"][:-6]
            #print(datePosted)

            # ingredients loop through the ingredient list
            ing = ""
            ingList = soup.find("ul", {"class": "recipe-list"})
            for li in ingList.find_all("li"):
                for span in li.find_all("span"):
                    ing += span.text.strip() + " "
                ing += "\n"
            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find_all("li", itemprop="recipeInstructions")
            for li in instrdiv:
                instr += li.text.strip() + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#foodandwine.com
    if "foodandwine.com" in url:
        try:
            # json and html scraping since the instructions are not in the json
            rawdata = soup.find('script', type='application/ld+json').text
            data = json.loads(soup.find('script', type='application/ld+json').text)
            data = data[2]
            #rawdata = data.text
            # title
            title = data['name'].strip()
            #print(title)
            # link
            link = url
            #print(link)
            # image link
            imglink = data['image']['url']
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = data['description']
            #print(descr)
            # date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # ingredients loop through the ingredient list
            ing = ""
            ingList = data['recipeIngredient']
            i = 0
            while i < len(ingList):
                ing += ingList[i].strip() + "\n"
                i += 1
            #print(ing)
            # instructions
            instr = data['recipeInstructions']
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#food.com / http://www.geniuskitchen.com
    if "geniuskitchen.com" in url:
        try:
            # json and html scraping since the instructions are not in the json
            rawdata = soup.find('script', type='application/ld+json').text
            data = json.loads(soup.find('script', type='application/ld+json').text)
            # title
            title = data['name']
            #print(title)
            # link
            link = url
            #print(link)
            # image link
            imglink = data['image']
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = data['description']
            #print(descr)
            # date published
            datePosted = data["datePublished"].replace("T", " ")[:-10]
            #print(datePosted)
            # ingredients loop through the ingredient list
            ing = ""
            ingList = data['recipeIngredient']
            i = 0
            while i < len(ingList):
                ing += ingList[i].strip() + "\n"
                i += 1
            #print(ing)
            # instructions
            instr = data['recipeInstructions']
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#foodnetwork.com
    if "foodnetwork.com" in url:
        try:
            # json and html scraping since the instructions are not in the json
            rawdata = soup.find('script', type='application/ld+json').text
            data = json.loads(soup.find('script', type='application/ld+json').text)
            # title
            title = data['name']
            #print(title)
            # link
            link = url
            #print(link)
            # image link
            imglink = data['image']['url']
            imgblob = imagegrabber(imglink)
            #print(imglink)
            # description
            descr = data['description']
            #print(descr)
            # date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')
            # ingredients loop through the ingredient list
            ing = ""
            ingList = data['recipeIngredient']
            i = 0
            while i < len(ingList):
                ing += ingList[i].strip() + "\n"
                i += 1
            #print(ing)
            # instructions
            instrList = data['recipeInstructions']
            i = 0
            instr = ""
            while i < len(instrList):
                instr += instrList[i] + "\n"
                i += 1

            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)
#foodnetwork.co.uk
    if "foodnetwork.co.uk" in url:
        try:
            # title
            title = soup.find("meta", property="og:title")
            title = title["content"]
            #print(title)
            # link
            link = soup.find("meta", property="og:url")
            link = link["content"]
            #print(link)

            # image link
            imglink = soup.find("meta", property="og:image")
            imglink = imglink["content"]
            imgblob = imagegrabber(imglink)
            #print(imglink)

            # description
            descr = soup.find("meta", property="og:description")
            descr = descr["content"]
            #print(descr)

            # date published
            datePosted = time.strftime('%Y-%m-%d %H:%M:%S')

            # ingredients loop through the ingredient list
            ing = ""
            ingList = soup.find("ul", {"class": "ingredient-list"})
            for li in ingList.find_all("li"):
                ing += li.text.strip() + " "
                ing += "\n"
            #print(ing)

            # instructions
            instr = ""
            instrdiv = soup.find("div", itemprop="recipeInstructions")
            for p in instrdiv.find_all("p"):
                instr += p.text + "\n"
            #print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe, (title, link, ing, descr, imglink, datePosted, instr, imgblob, siteid))
                    db.commit()

        except:
            print("no recipe found @ %s" % url)

#delish.com
    if "delish.com" in url:
        try:
            # json and html scraping since the instructions are not in the json
            rawdata = soup.find('script', type='application/ld+json').text
            data = json.loads(soup.find('script', type='application/ld+json').text)
            # title
            title = data['name']
            # print(title)
            # link
            link = url
            # print(link)
            # image link
            imglink = soup.find("meta", property="og:image")
            imglink = imglink["content"]
            imgblob = imagegrabber(imglink)
            # print(imglink)
            # description
            descr = data['description']
            # print(descr)
            # date published
            datePosted = data["datePublished"].replace("T", " ")[:-10]
            # print(datePosted)
            # ingredients loop through the ingredient list
            ing = ""
            ingList = data['recipeIngredient']
            i = 0
            while i < len(ingList):
                ing += ingList[i].strip() + "\n"
                i += 1
            # print(ing)
            # instructions
            instr = data['recipeInstructions']
            # print(instr)
            if urlValidate(link) == 0:
                if ing:
                    print("title:%s" % title)  # print title
                    print("Date published %s" % datePosted)
                    print("Url: %s" % link)
                    print("Description: %s" % descr)
                    print("imglink: %s" % imglink)  # print image source
                    print("ingredients: %s" % ing)  # print ingredients
                    print("instructions: %s" % instr)
                    add_recipe = "insert into recipes (title, link, ingredients, description, image ,dateposted, instructions, jsondata, imageblob, siteid) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(add_recipe,(title, link, ing, descr, imglink, datePosted, instr, rawdata, imgblob, siteid))
                    db.commit()
        except:
            print("no recipe found @ %s" % url)

    #must stay at end to release soup from memory
    soup.decompose()
