###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from __future__ import print_function
from os import environ

from twisted.internet.defer import inlineCallbacks

from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from autobahn.wamp.types import PublishOptions, SubscribeOptions, CallOptions, RegisterOptions

ENCRYPTION_KEY = u'z1JePdJbQkbRCWjldZYImgj5hpsZ2cEtX7CQmQmdta4='

from nacl.public import PrivateKey
from nacl.encoding import Base64Encoder

from autobahn.wamp.keyring import KeyRing


class Component(ApplicationSession):
    """
    An application component that publishes an event every second.
    """
    NUM = 3

    @inlineCallbacks
    def onJoin(self, details):
        print("session attached")
        self._keyring = KeyRing()

        key = PrivateKey(ENCRYPTION_KEY, encoder=Base64Encoder)
        self._keyring.add(u'com.myapp.topic2', key)
        self._keyring.add(u'com.myapp.proc2', key)

        yield self._test_rpc()
        yield self._test_pubsub()

        self.leave()

    @inlineCallbacks
    def _test_rpc(self):

        def add2(a, b, details=None):
            print("call received: a={}, b={}, details={}".format(a, b, details))
            return a + b

        options = RegisterOptions(details_arg='details')
        reg1 = yield self.register(add2, u'com.myapp.proc1', options=options)
        reg2 = yield self.register(add2, u'com.myapp.proc2', options=options)

        options = CallOptions(disclose_me=True)
        counter = 1
        while counter <= self.NUM:
            res = yield self.call(u'com.myapp.proc1', 23, counter, options=options)
            print("called: {}".format(res))
            res = yield self.call(u'com.myapp.proc2', 23, counter, options=options)
            print("called: {}".format(res))
            yield sleep(1)
            counter += 1

        yield reg1.unregister()
        yield reg2.unregister()

    @inlineCallbacks
    def _test_pubsub(self):

        def on_message(msg, details=None):
            print("event received: msg='{}', details={}".format(msg, details))

        options = SubscribeOptions(details_arg='details')
        sub1 = yield self.subscribe(on_message, u'com.myapp.topic1', options=options)
        sub2 = yield self.subscribe(on_message, u'com.myapp.topic2', options=options)

        options = PublishOptions(acknowledge=True, exclude_me=False, disclose_me=True)
        counter = 1
        while counter <= self.NUM:
            msg = u"Counter is at {}".format(counter)
            pub = yield self.publish(u'com.myapp.topic1', msg, options=options)
            print("published: {}".format(pub))
            pub = yield self.publish(u'com.myapp.topic2', msg, options=options)
            print("published: {}".format(pub))
            yield sleep(1)
            counter += 1

        yield sub1.unsubscribe()
        yield sub2.unsubscribe()

    def onLeave(self, details):
        self.disconnect()

    def onDisconnect(self):
        from twisted.internet import reactor
        reactor.stop()


if __name__ == '__main__':
    runner = ApplicationRunner(u"ws://127.0.0.1:8080", u"realm1")
    runner.run(Component)
