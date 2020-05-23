#!/usr/bin/env python3
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from collections import namedtuple
from collections import deque
from PIL import Image
from time import sleep
import sys, logging, argparse, random
import itertools

import notify2
def Notify(msg):
    notify2.init('Notification')
    n = notify2.Notification(msg)
    n.set_urgency(notify2.URGENCY_NORMAL)
    n.show()

HomeUrl = "https://pixelplanet.fun"  
FormatUrl = "https://pixelplanet.fun/#d,{},{},16"
Pos = namedtuple('Pos', 'x y')
Color = namedtuple('Color', 'r g b')

class Direction:
    LEFT = 0
    RIGHT =1
    DOWN = 2
    UP = 3 

class BotInterception(Exception):
    pass
    
class PixelPlanetBot:
    Colors = (Color(255, 255, 255), Color(228, 228, 228), Color(196, 196, 196), \
              Color(136, 136, 136), Color(78, 78, 78), Color(0, 0, 0), \
              Color(244, 179, 174), Color(255, 167, 209), Color(255, 84, 178), \
              Color(255, 101, 101), Color(229, 0, 0), Color(154, 0, 0), \
              Color(254, 164, 96), Color(229, 149, 0), Color(160, 106, 66), \
              Color(96, 64, 40), Color(245, 223, 176), Color(255, 248, 137), \
              Color(229, 217, 0), Color(148, 224, 68), Color(2, 190, 1),  \
              Color(104, 131, 56), Color(0, 101, 19), Color(202, 227, 255), \
              Color(0, 211, 221), Color(0, 131, 199), Color(0, 0, 234), \
              Color(25, 25, 115), Color(207, 110, 228), Color(130, 0, 128))

    def __init__(self, x, y, headless=False, debug=True):
        self.formatter = logging.Formatter('[%(funcName)24s] %(message)s')
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(self.formatter)
        self.console_handler.setLevel(logging.INFO)
                
        self.log = logging.getLogger("PixelPlanetBot")  
        self.log.addHandler(self.console_handler)
        self.log.setLevel(logging.DEBUG)
        
        if debug: 
            self.file_handler = logging.FileHandler(filename="pixelplanetbot.log", mode="w")
            self.file_handler.setFormatter(self.formatter)
            self.file_handler.setLevel(logging.DEBUG)                
            self.log.addHandler(self.file_handler)
            
        self.log.debug(f'Start logging')
        self.headless = headless
        if self.headless:
            self.chrome_options = webdriver.ChromeOptions()
            self.chrome_options.add_argument('--headless')
            self.chrome_options.add_argument('--disable-gpu')
            self.chrome_options.add_argument('--window-size=800,600')            
            self.driver = webdriver.Chrome(options=self.chrome_options)
        else:
            self.driver = webdriver.Chrome()

        self.driver.get(FormatUrl.format(x, y))
        self.UpdateElements();
        self.center = Pos(x, y)
        self.color = self.Colors[0]
    
    def __enter__(self):
        return self
    def __exit__(self, *a):
        self.driver.quit()
    
    def _move_to_element(self, elem):
        self.log.debug(elem.tag_name)
        self.CheckAccess()
        ActionChains(self.driver).move_to_element(elem).perform()
        
    def _move_by_offset(self, x, y):
        self.log.debug(f'To ({x}, {y})')
        self.CheckAccess()
        try:
            ActionChains(self.driver).move_to_element(self.canvas) \
                .move_by_offset(x, y).perform()
        except MoveTargetOutOfBoundsException as e:
            self.log.error(str(e))
            self.OnCaptcha()
        
    def _click_on_element(self, elem=None):
        self.CheckAccess()
        if elem:
            self.log.debug(elem.tag_name)        
            elem.click()
        else:
            self.log.debug('Just click')
            ActionChains(self.driver).click().perform()
            
    def _send_keys(self, keys):
        self.log.debug(f'Keys = {repr(keys)}')        
        self.CheckAccess()
        ActionChains(self.driver).send_keys(keys).perform()        
    
    def UpdateElements(self):
        self.log.debug('...')
        self.captcha = self.driver.find_element_by_xpath('/html/body/div/div/iframe/../..')
        self.canvas = self.driver.find_element_by_tag_name('canvas')
        self.cooldownbox = self.driver.find_element_by_xpath('//div[@class="cooldownbox"]|//div[@class="cooldownbox show"]')
        self.coorbox = self.driver.find_element_by_class_name('coorbox')
        
    def PickColor(self, r, g, b):
        self.log.debug(str(Color(r, g, b)))
        old_color = self.color
        try:
            if Color(r, g, b) != self.color: 
                try:
                    self.color = self.Colors[self.Colors.index((r, g, b))]
                except ValueError:
                    self.log.error(f'Invalid color rgb({r}{g}{b})')
                    return                
            
            xpath = f'//span[@color=\'rgb({self.color.r}, {self.color.g}, {self.color.b})\']'        
            try:
                elem = self.driver.find_element_by_xpath(xpath)
            except NoSuchElementException:
                self.log.error('No such element for specified color found') 
                self.color = old_color
                
            self._click_on_element(elem)
        except ElementClickInterceptedException as e:
            self.log.error(str(e))                
            self.OnCaptcha()
            
    def MoveScreenInDirection(self, direc):
        self.log.debug(f'Direction = {direc}')
        keys = {            
            Direction.LEFT: Keys.ARROW_LEFT,
            Direction.RIGHT: Keys.ARROW_RIGHT,
            Direction.UP: Keys.ARROW_UP,
            Direction.DOWN: Keys.ARROW_DOWN
        }
        
        self._send_keys(keys[direc])
        self.UpdateCenter()        
                
    def MoveCursor(self, x, y):              
        self.log.debug(f'From {self.center} to {Pos(x, y)}')
        
        step = 3
        offset = Pos(step * (x - self.center.x), step * (y - self.center.y))
            
        self.log.debug(f'Offset = {offset}')
        self._move_by_offset(*offset) # Set cursor according to offset                
        
        # Adjusting coords
        cur = self.getMouseCoord()
        if cur != Pos(x, y):
            self.log.debug(f'Adjusting coordinates from {cur} to {Pos(x, y)}')
            step = 2
            offset = \
                Pos(offset.x + step*(x - cur.x),
                    offset.y + step*(y - cur.y))
            self._move_by_offset(*offset)
            self.log.debug(f'Adjusted offset = {offset}, adjusted coordinates = {self.getMouseCoord()}')
    
    def CoordOnScreen(self, x, y): 
        rec_size = 100
        self.log.debug(f'From {self.center} to ({x}, {y})')       
        return abs(self.center.x - x) < rec_size/2 and \
               abs(self.center.y - y) < rec_size/2
        
    def CoordRelativeToCentre(self, x, y):                
        self.log.debug(f'Center = {self.center}, {Pos(x, y)}')
        if self.center == Pos(x, y):
            return
        rec_size = 100
        suby = self.center.y - y
        subx = self.center.x - x
        part = 1 # 4 + (suby > 0)*(-2) + (subx > 0)*(-1)
        if suby < 0: part = (4 if subx < 0 else 3)
        else: part = (2 if subx < 0 else 1)
        
        if subx == 0:
            return Direction.UP if part <= 2 else Direction.DOWN

        side1pt = Pos(self.center.x + rec_size/2 - 1, suby*rec_size/subx + self.center.y)        
        
        if self.CoordOnScreen(*side1pt):
            return Direction.RIGHT if part%2 == 0 else Direction.LEFT
        else:
            return Direction.UP if part <= 2 else Direction.DOWN
            
    def Move(self, x, y):
        self.log.debug(f'({x}, {y})')
        if self.CoordOnScreen(x, y):
            self.MoveCursor(x, y)
        else:
            while not self.CoordOnScreen(x, y):
                direc = self.CoordRelativeToCentre(x, y)
                self.MoveScreenInDirection(direc)
            self.MoveCursor(x, y)
                     
    def getCoolDownTime(self):
        time = [int(i.zfill(1)) for i in self.cooldownbox.text.split(':')]
        if len(time) == 2:
            mins,secs = time[0],time[1]
        else:
            mins,secs = 0,time[0]
        res = secs + 60*mins
        self.log.debug(f'Time (sec.) = {res}')
        return res
        
    def getMouseCoord(self):        
        # (201, -5)
        temp = self.coorbox.text.split(',')
        x, y = int(temp[0][1:]), int(temp[1][:-1].strip())
        self.log.debug(f'MouseCoord (world coords) = ({x}, {y})')
        return Pos(x, y)
    
    def UpdateCenter(self):
        self._move_to_element(self.canvas)
        self.center = self.getMouseCoord()
    
    def UpdatePage(self): 
        self.log.debug('...')   
        self.driver.refresh()
        self.UpdateElements()
        self.UpdateCenter()
        
    def CheckAccess(self):
        # Checking captcha
        style = self.captcha.get_attribute('style')
        v = style.find('visibility')
        visibility = style[style.find(':', v)+1:style.find(';', v)].strip()
        self.log.debug(f'Captcha visibility = {visibility}')
        if visibility == 'visible':
            self.log.error('Captcha has appeared')
            self.OnCaptcha()
            return
            
        # Checking failed network connection
        try:
            swal = self.driver.find_element_by_class_name('swal2-shown')
            self.log.error('Didn\'t get an answer from pixelplanet.')
            self.OnCaptcha()
        except NoSuchElementException:
            return                
        
    def OnCaptcha(self):
        self.log.error('An unexpected prolem has occured (it maybe captcha or failed network connection).')                
        if self.headless:
            self.UpdatePage()	
        raise BotInterception()        
    
    def DrawPoint(self, x, y): # Interact directly with webdriver 
        self.log.debug(f'In ({x}, {y})')
        self.Move(x, y)        
       
        wait = self.getCoolDownTime() - 53
        sleep(max(0, wait)) 
        
        try:    
            self._click_on_element()
        # Exception raises when captcha's been already appeared so the last pixel
        # is waiting for the captcha resolving and hasn't been drawn on the map yet
        except ElementClickInterceptedException as e:
                self.log.error(str(e))
                self.OnCaptcha()
            
def drawPixel(bot, cx, cy, rgb):
    intercepted = False
    while True:                                          
        try:        
            bot.PickColor(*rgb)
            cooldown = bot.getCoolDownTime()
            bot.DrawPoint(cx, cy)
            break
        except BotInterception:
           Notify('A problem has occured that needs your attention.')        
           input('Press Enter to continue drawing if the problem\'s been solved...')
           intercepted = True
    return not intercepted

def shuffle(indices, method):
    res = None
    print(f'Shuffling with method: {method}')
    if method == 'chessboard':
        odd_indices = (i for i in indices if (i[0]+i[1])%2)
        even_indices = (i for i in indices if not (i[0]+i[1])%2)
        res = itertools.chain(even_indices, odd_indices)
    elif method == 'random':
        # Ensures getting the same shuffle for same data arrays
        random.seed(1024)
        res = sorted(iter(indices), key=lambda k: random.random())
    else:
        res = indices
    print('Shuffling done')
    return res
        
def main():
    parser = argparse.ArgumentParser(description='PixelPlanet.fun bot based on Selenium')    
    parser.add_argument('x', action='store', type=int, help='the initial x coordinate to start drawing image from')
    parser.add_argument('y', action='store', type=int, help='the initial y coordinate')
    parser.add_argument('image', action='store', help='image to draw')
    parser.add_argument('--step', metavar='N', action='store', help='step to start drawing the image', type=int, default=0) 
    parser.add_argument('--headless', action='store_true', help='do not display Chrome UI')
    parser.add_argument('--direction', action='store', default='horizontal', \
        choices=['horizontal', 'vertical'], help='set specific drawing direction ("step" is specific to each direction)')  
    parser.add_argument('--method', action='store', default='default', \
        choices=['default', 'chessboard', 'random'], help='set specific drawing method ("step" is specific to each method)')  
    args = parser.parse_args()
    
    with Image.open(args.image) as im:
        pix = im.load()
        size = im.size
    
    # If program receives SIGTERM or SIGINT, it'll be able to close headless browser safely
    with PixelPlanetBot(args.x, args.y, headless=args.headless, debug=True) as bot:
        step = 0
        
        ix, iy = 1, 0             
        if args.direction == 'vertical':
            ix, iy = 0, 1
                
        indices = itertools.product(range(size[ix]), range(size[iy]))
        indices = shuffle(indices, args.method)
        
        pixels = deque(maxlen=6)
        for i in indices:
            cur_img_pos = Pos(i[ix], i[iy])
            if pix[cur_img_pos][3] < 0.2 * 255: 
                continue
            step += 1
            if step < args.step:
                continue            
            cur_coord = Pos(args.x + cur_img_pos.x, args.y + cur_img_pos.y)
            if drawPixel(bot, cur_coord.x, cur_coord.y, pix[cur_img_pos][:3]) == False:                
                # Most likely a few last pixels wasn't drew either                
                for j in pixels:
                    img_pos = Pos(j[ix], j[iy])
                    coord = Pos(args.x + img_pos.x, args.y + img_pos.y)
                    drawPixel(bot, coord.x, coord.y, pix[img_pos][:3])
                    print(f'[Revision] {coord} colored, time = {bot.getCoolDownTime()}')                     
                    sleep(0.2)
                    
            print(f'[Step {step}] {cur_coord} colored, image[{cur_img_pos.x}, {cur_img_pos.y}], time = {bot.getCoolDownTime()}')
            pixels.append(i)
            sleep(0.2)
        Notify('Work has done')
                            
if __name__ == '__main__':
    main()    