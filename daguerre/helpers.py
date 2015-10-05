from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from subprocess import check_output

from progressbar import Bar, Counter, ETA, Percentage, ProgressBar
import notify2


def generate_progress_bar(title, number_of_elements):
    widgets = [title,
               Counter(),
               '/%s ' % number_of_elements,
               Percentage(),
               ' ',
               Bar(left='[', right=']', fill='-'),
               ' ',
               ETA()]
    return ProgressBar(widgets=widgets, maxval=number_of_elements).start()


def notify_this(text):
    notify2.init("daguerre")
    n = notify2.Notification("Daguerre", text, "camera-photo")
    n.set_timeout(2000)
    n.show()


def run_in_parallel(function, source_list, title, num_workers=cpu_count() + 1):
    results = []
    if source_list:
        cpt = 0
        progress_bar = generate_progress_bar(title, len(source_list)).start()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(function, el): el for el in source_list}
            for future in as_completed(futures):
                results.append(future.result())
                cpt += 1
                progress_bar.update(cpt)
        progress_bar.finish()
    return results


def exiftool(fields, path):
    return check_output(["/usr/bin/vendor_perl/exiftool", "-s3"] + fields + [path.as_posix()]).strip()
