# coding: utf8
import urllib2
import datetime
import time
import threading
import sys
import re

QUERY_URL_FORMAT = "https://%s/otn/leftTicket/queryT?leftTicketDTO.train_date=2015-02-12&" \
                   "leftTicketDTO.from_station=GZQ&leftTicketDTO.to_station=BJP&purpose_codes=ADULT"


class Faster(object):
    def __init__(self, hostname, hosts):
        self.hostname = hostname
        self.hosts = hosts

    def fetch_all_update_time(self):
        threads = []
        results = []
        lock = threading.Lock()

        def results_append(*args):
            lock.acquire()
            results.append(args)
            lock.release()

        for host in self.hosts:
            req = urllib2.Request(QUERY_URL_FORMAT % host, headers={"Host": self.hostname})
            thread_func = self.__class__._fetch_update_time
            t = threading.Thread(name=host, target=thread_func, args=(host, req, results_append))
            t.setDaemon(True)
            t.start()
            t.host = host
            threads.append(t)

        for t in threads:
            t.join()

        return results

    @staticmethod
    def _fetch_update_time(host, req, result_func):
        try:
            res = urllib2.urlopen(req, timeout=2)
            update = res.info()["Date"]
            d = datetime.datetime.strptime(update, "%a, %d %b %Y %H:%M:%S %Z")
            d = d.replace(hour=d.hour+8)
            result_func(host, time.mktime(d.timetuple()), res)
        except Exception, e:
            sys.stderr.write("%s: %s(%s)\n" % (host, e, type(e)))
            pass

    def fastest(self):
        hosts_update_time = self.fetch_all_update_time()
        max_host, max_time, max_r = hosts_update_time[0]
        min_host, min_time = max_host, max_time
        for h, t, r in hosts_update_time:
            if t > max_time:
                max_host = h
                max_r = r
            if t < min_time:
                min_host = h

        print "@@ ", time.strftime("%H:%M:%S")
        print "%d available hosts" % len(hosts_update_time)
        print "slowest: %s %d, fastest: %s %d(%s)" % (
            min_host, min_time, max_host, max_time, time.strftime("%H:%M:%S", time.localtime(max_time)))
        print "fastest info: ", filter(lambda x: "wz_num" not in x,
                                       re.findall(r'"[a-z]{2}_num":"(?:[0-9]+|有)"', max_r.read()))
        return max_host

    def fetch_available_hosts(self):
        hosts_update_time = self.fetch_all_update_time()
        return [h for h, t, r in hosts_update_time]


class DomainHosts(object):
    """获取域名解析到的的所有主机IP"""

    _query_url_format = "http://tool.17mon.cn/dns.php?a=dig&area[]=china&host=%s"
    import re
    _ip_re = re.compile(r"(?:[0-9]{0,3}\.){3}[0-9]{0,3}")

    def __init__(self, domain):
        self.domain = domain

    def fetch_hosts(self):
        url = self._query_url_format % self.domain
        res = urllib2.urlopen(url)
        return self._ip_re.findall(res.read())


def fetch_12306_hosts():
    sys.stdout.write("fetching 12306 hosts ...\n")
    return Faster("kyfw.12306.cn", DomainHosts("kyfw.12306.cn").fetch_hosts()).fetch_available_hosts()


def fastest_12306(hosts):
    if isinstance(hosts, str):
        hosts = [x.strip() for x in open(hosts).readlines()]

    print Faster("kyfw.12306.cn", hosts).fastest()

if __name__ == "__main__":
    try:
        from gevent import monkey
        monkey.patch_all()
    except Exception, _:
        pass

    if len(sys.argv) < 2:
        sys.stderr.write("Usage: %s <--fetch|HOSTS_FILE>\n")
        sys.exit(1)

    if sys.argv[1] == "--fetch":
        fetch_12306_hosts()
    else:
        while 1:
            st = time.time()
            fastest_12306(sys.argv[1])
            print "================================================"
            sleep_time = 5 - (time.time()-st)
            if sleep_time > 0:
                time.sleep(sleep_time)