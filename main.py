import os
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import json
import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

log_filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
log_filepath = os.path.join(log_dir, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath, encoding='utf-8')
    ]
)

"""
In the same directory create a config.json file which has 3 values: login, password, url and session length
URL is supposed to be your course url, https://studia-online.pl/kurs/{COURSE_N} - check manually on the webstie
Session length terminates the script as the worktime exceeds the desired finish time (always finishes video before checking)
"""
def check_if_should_finish(desired_finish_time:datetime.datetime):
    if datetime.datetime.now() > desired_finish_time: 
        logging.info("Exceeded finish time, closing the browser")
        exit()
    
def play_materials():
    with open('config.json', encoding='UTF-8') as f:
        data = json.loads(f.read())
        LOGIN = data['login']
        PASSWORD = data['password']
        URL = data['url']
        SESSION_LENGTH_IN_MINUTES = data['session_length_in_minutes']
        DESIRED_FINISH_TIME = datetime.datetime.now() + datetime.timedelta(0, SESSION_LENGTH_IN_MINUTES*60)
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500, args=['--start-maximized'])
        browser.new_context(no_viewport=True)
        
        context = browser.new_context()
        page = context.new_page()

        try:
            logging.info("Navigating to website")
            page.goto(URL)

            logging.info("Accepting cookies")
            page.locator(".cky-btn-accept").first.click()
            
            logging.info("Filling login")
            page.locator("#login").first.fill(LOGIN)
            
            logging.info("Filling password")
            page.locator("#pass").first.fill(PASSWORD)
            
            logging.info("Logging in")
            page.locator(".btn-primary").first.click()
            
            page.wait_for_url("**/dashboard*", timeout=5000)
            
            logging.info("Go to course url")
            page.goto(URL)
            
            logging.info("Dissmiss session info button")
            page.locator(".exam-section__modal--btn").first.click()
            
            classes = page.locator(".course-topic__list").locator(".course-topic").all()
            
            IMG_URL = "https://studia-online.pl/images/course/new_layout/completed.svg"
            clean_subjects = [
                el for el in classes 
                if el.locator(f'img[src="{IMG_URL}"]').count() == 0
            ]
            
            for subject in clean_subjects:
                logging.info("Picking subject")
                subject.locator(".course-topic__link").first.click()
                time.sleep(1.5)
                
                lessons = page.locator(".course-lesson").all()
                clean_lessons = [
                    el for el in lessons 
                    if el.locator(f'img[src="{IMG_URL}"]').count() == 0
                ]
                
                for lesson in clean_lessons:
                    logging.info("Clicking lesson")
                    lesson.locator(".course-lesson__link").first.click()
                    videos = page.locator(
                        '.course-material__progress-area:not(:has-text("100%"))'
                    ).locator("+ span > .video-js").all()
                    presentation = page.locator(".pdf-container").first
                    
                    for video in videos:
                        check_if_should_finish(DESIRED_FINISH_TIME)
                        logging.info("Starting Video")
                        video.click(force=True)
                        time.sleep(3)
                        str_time = video.locator(".vjs-remaining-time-display").first.text_content().split(':')
                         
                        duration = int(str_time[0])*3600 + int(str_time[1])*60 + int(str_time[2])
                        
                        time.sleep(duration)
                    
                    # wait for presentation progress to finish
                    progress_locator = presentation.locator(
                            "xpath=preceding-sibling::div[contains(@class, 'course-material__progress-area')][1]"
                        ).locator(".course-material__progress-text")
                    
                    logging.info("Waiting for presentation to finish")
                    
                    while True:
                        progress_text = progress_locator.text_content()
                        
                        if progress_text and "100%" in progress_text:
                            logging.info("Presentation finished (100%)!")
                            break
                        
                        logging.info(f"Current progress: {progress_text.strip() if progress_text else 'Unknown'}. Checking again in 60s...")
                        check_if_should_finish(DESIRED_FINISH_TIME)
                        time.sleep(60)
                        
        except PlaywrightTimeoutError:
            logging.error("An element took too long to load or could not be found.", exc_info=True)
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        finally:
            browser.close()

if __name__ == "__main__":
    play_materials()