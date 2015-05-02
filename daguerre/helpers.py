from daguerre.checks import *

import notify2

def generate_pbar(title, number_of_elements):
    widgets = [title, Counter(), '/%s '%number_of_elements, Percentage(), ' ', Bar(left='[',right=']', fill='-'),' ', ETA()]
    return ProgressBar(widgets = widgets, maxval = number_of_elements).start()


def notify_this(text):
    notify2.init("daguerre")
    n = notify2.Notification("Daguerre",
                             text,
                             "camera-photo")
    n.set_timeout(2000)
    n.show()
