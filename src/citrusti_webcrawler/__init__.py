import asyncio
import aiohttp
import regex as re
import bs4

RE_ROBOTS = re.compile(r"([A-Za-z0-9-]+): (.+)")

async def requests(url):
    headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.9 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.text()

async def get_robots_txt(src):
    # print(f"Getting robots.txt for {src}")
    url = f"{src}/robots.txt"
    return await requests(url)

async def parse_robots_txt(robots_txt):
    # print(f"Parsing robots.txt")
    categories = {}
    for line in robots_txt.split("\n"):
        match = RE_ROBOTS.match(line)
        if match:
            category, value = match.groups()
            if category not in categories:
                categories[category] = []
            categories[category].append(value)
    return categories

async def re_not_permitted(category):
    RE_SPECIALS = re.compile(r"([.+?])")
    RE_ASKTERISK = re.compile(r"([*])")
    disallowed = ["(" + RE_ASKTERISK.sub(".*", RE_SPECIALS.sub(r"\\\g<1>", x)) + ")" for x in category.get("Disallow", [])]
    allowed = ["(" + RE_ASKTERISK.sub(".*", RE_SPECIALS.sub(r"\\\g<1>", x)) + ")" for x in category.get("Allow", [])]
    combined_re = r"({0})|(?!({1}))".format("|".join(disallowed), "|".join(allowed))
    
    # print(f"Generated regex: {combined_re}")
    return re.compile(combined_re)

async def get_links_from_sitemap(sitemap, not_allowed):
    # print(f"Getting links from sitemap {sitemap}")
    sitemap = await requests(sitemap)
    soup = bs4.BeautifulSoup(sitemap, "xml")
    sitemaps = soup.find_all("sitemap")
    sitemap_tasks = []
    for sitemap in sitemaps:
        for loc in sitemap.find_all("loc"):
            sitemap_tasks.append(asyncio.create_task(get_links_from_sitemap(loc.text, not_allowed)))
    links = await asyncio.gather(*sitemap_tasks)
    links = {link for sublist in links for link in sublist}
    urls = soup.find_all("url")
    for url in urls:
        for loc in url.find_all("loc"):
            if not not_allowed.match(loc.text):
                links.add(loc.text)
    return links

async def scrape(src):
    # print(f"Scraping {src}")
    robots_txt = await get_robots_txt(src)
    categories = await parse_robots_txt(robots_txt)
    not_allowed = await re_not_permitted(categories)
    for sitemap in categories.get("Sitemap"):
        links = await get_links_from_sitemap(sitemap, not_allowed)
        print(links)
