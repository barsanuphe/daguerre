from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count

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

def run_in_parallel(function, source_list, title, num_workers=cpu_count()+1):
    results = []
    if source_list != []:
        cpt = 0
        pbar = generate_pbar(title, len(source_list)).start()
        with ThreadPoolExecutor(max_workers = num_workers) as executor:
            futures = {executor.submit(function, el): el for el in source_list}
            for future in as_completed(futures):
                results.append(future.result())
                cpt +=1
                pbar.update(cpt)
        pbar.finish()
    return results
