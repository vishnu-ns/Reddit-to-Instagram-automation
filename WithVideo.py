import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime

import pandas as pd
import praw
import requests
from better_profanity import profanity
from pytz import timezone

start = time.time()
print('running...')

INSTAGRAM_APP_ID = os.environ['INSTAGRAM_APP_ID']
IG_USER_ID = os.environ['IG_USER_ID']

IMGUR_CLIENT_ID = os.environ['IMGUR_CLIENT_ID']
IMGUR_CLIENT_SECRET = my_secret = os.environ['IMGUR_CLIENT_SECRET']

REDDIT_CLIENT_SECRET = os.environ['REDDIT_CLIENT_SECRET']
REDDIT_CLEINT_ID = os.environ['REDDIT_CLEINT_ID']
INSTAGRAM_APP_SECRET = os.environ['INSTAGRAM_APP_SECRET']

IMGUR_UPLOAD_URL = "https://api.imgur.com/3/upload.json"

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'

# valid for two months]
USER_ACCESS = os.environ['USER_ACESS']

# logging
logging.basicConfig(filename='logs.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)

# database added
df = pd.read_csv('my_reddit_meme_posts.csv')
database_links = df['short_link'].tolist()

# Task 1 Get the reddit posts
red = praw.Reddit(client_id=REDDIT_CLEINT_ID,
                  client_secret=REDDIT_CLIENT_SECRET,
                  user_agent=USER_AGENT)

subred = red.subreddit('Animemes').hot(limit=50)

# & (i.shortlink not in db['my_reddit_db']['short_link'])
red_post = None
for i in subred:
    if (i.stickied is False) & (i.over_18 is False) & (i.shortlink not in database_links):
        if i.secure_media is None:

            # only image
            if bool(i.preview['images'][0]['variants']):
                only_image = True
                meta = i.preview['images'][0]['variants']['mp4']['source']
                width = meta['width']
                height = meta['height']
                aspect_ratio = width / height
                if (aspect_ratio >= 0.8) & (aspect_ratio <= 1.19):
                    red_post = i
                    long_url = meta['url']
                    break

            # gif without video
            else:
                only_image = False
                meta = i.preview['images'][0]['source']
                width = meta['width']
                height = meta['height']
                aspect_ratio = width / height
                if (aspect_ratio >= 0.8) & (aspect_ratio <= 1.19):
                    red_post = i
                    long_url = meta['url']
                    break

        else:
            # gif with video and video
            meta = i.secure_media['reddit_video']
            width = meta['width']
            height = meta['height']
            aspect_ratio = width / height
            print(aspect_ratio)
            if (aspect_ratio >= 0.8) & (aspect_ratio <= 1.19):
                v_url = i.secure_media['reddit_video']['fallback_url']
                video_size = size = requests.head(v_url).headers['Content-Length']
                video_size_MB = int(video_size) / (1024 * 1024)
                print(video_size_MB)
                if video_size_MB < 8:
                    only_image = False
                    red_post = i
                    long_url = meta['fallback_url'].split('?')[0]
                    break

if red_post:
    if only_image is False:
        print('the post is either a gif or a video')
    # red_image_url = red_post.preview['images'][0]['source']['url']
    short_link = red_post.shortlink
    caption = red_post.title
    redditor = red_post.author.name



else:
    print('red post not defined')
    logger.fatal('reddit post didn\'t have a valid image post increase the limit!')
    raise Exception

# removing any curse words if any
caption = profanity.censor(caption, censor_char='💩')

# adding extra bio
caption_final = caption + f"\n👉Follow ---> @reddit.memes.top\n👉New popular meme every hour guaranteed\n\n-----------------------------\n😏Credits are never unknown\n👉OP --> u/{redditor}\n{short_link}\n-----------------------------\n\nHashtags - \n#reddit #redditmemes #memesdaily #meme #memes #dailymemes #everyhour"

caption_encoded = urllib.parse.quote(caption_final.encode('utf8'))
unique_id = short_link.split('/')[-1]

# for image
data = {
    'image': long_url,
    'type': 'URL',
    'name': f'{unique_id}.jpg',
    'title': caption,
    'privacy': 'public',
}

headers = {
    "Authorization": f"Client-ID {IMGUR_CLIENT_ID}"
}

r_imgur = requests.post(
    IMGUR_UPLOAD_URL,
    headers=headers,
    data=data
)

imgur_link_jpg = None
try:
    imgur_link = r_imgur.json()['data']['link']
    imgur_link_jpg = '.'.join(imgur_link.split('.')[:-1]) + '.jpg'

    df.to_csv('my_reddit_meme_posts.csv', index=False)
# df.to_csv('copy_my_reddit_database.csv', index=False)

except Exception as e:
    logger.error(e)

container_id = None

if only_image:
    posting_url = f'https://graph.facebook.com/v13.0/{IG_USER_ID}/media?image_url={imgur_link_jpg}&caption={caption_encoded}&access_token={USER_ACCESS}'

else:
    posting_url = f'https://graph.facebook.com/v13.0/{IG_USER_ID}/media?video_url={long_url}&media_type=VIDEO&caption={caption_encoded}&access_token={USER_ACCESS}'

# post meme on my instagram
r_container = requests.post(posting_url)
if r_container.status_code == 200:
    container_id = r_container.json()['id']

else:
    logger.fatal(f'status is not 200 but it is {r_container.status_code} and value is {r_container.text}')

# posting

if container_id:
    print(container_id)
    print('sleeping for a minute')
    time.sleep(60)
    publish_url = f'https://graph.facebook.com/v13.0/{IG_USER_ID}/media_publish?creation_id={container_id}&access_token={USER_ACCESS}'
    try:
        lim = requests.get(
            f'https://graph.facebook.com/v13.0/{IG_USER_ID}/content_publishing_limit?fields=quota_usage,rate_limit_settings&access_token={USER_ACCESS}')
        lim_num = lim.json()['data'][0]['quota_usage']
        lim_num = int(lim_num)
        lim_left_before = 25 - lim_num
        lim_left_after = lim_left_before - 1
        print(lim_left_after, 'posts left!')

        if lim_num <= 25:
            r_publish = requests.post(publish_url)
            print(r_publish.text)
            # print(r_publish.json()['id'])
            print('Post is live!')
            logger.log(10, f'{lim_left_after} posts left')

        else:
            logger.fatal(f'limit exhausted! {lim_left_after} left')
            print('fatal error, no post left please stop!')
            logger.fatal(f'what!, {r_publish.text}')
            raise FutureWarning

    except Exception as e:
        logger.log(10, e)

end = time.time()
ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%Y-%m-%d %I:%M:%S %p')
print('I ran at', ind_time)
logger.info(f"Post created at {ind_time}")
print('Run time ', round(end - start, 2), 'seconds')
