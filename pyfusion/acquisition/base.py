"""Base classes for  pyfusion data acquisition. It is  expected that the
base classes  in this module will  not be called  explicitly, but rather
inherited by subclasses in the acquisition sub-packages.

"""
from numpy.testing import assert_array_almost_equal
from pyfusion.conf.utils import import_setting, kwarg_config_handler, \
     get_config_as_dict, import_from_str
from pyfusion.data.timeseries import Signal, Timebase, TimeseriesData
from pyfusion.data.base import ChannelList
from pyfusion.debug_ import debug_
import traceback
import sys
import pyfusion  # only needed for .VERBOSE and .DEBUG

class BaseAcquisition(object):
    """Base class for datasystem specific acquisition classes.

    :param   config_name:  name   of  acquisition   as  specified in\
    configuration file.

    On  instantiation,  the pyfusion  configuration  is  searched for  a
    ``[Acquisition:config_name]``   section.    The   contents  of   the
    configuration  section are  loaded into  the object  namespace.  For
    example, a configuration section::

      [Acquisition:my_custom_acq]
      acq_class = pyfusion.acquisition.base.BaseAcquisition
      server = my.dataserver.com
 
    will result in the following behaviour::

     >>> from pyfusion.acquisition.base import BaseAcquisition
     >>> my_acq = BaseAcquisition('my_custom_acq')
     >>> print(my_acq.server)
     my.dataserver.com

    The configuration entries can be overridden with keyword arguments::

     >>> my_other_acq = BaseAcquisition('my_custom_acq', server='your.data.net')
     >>> print(my_other_acq.server)
     your.data.net

    """
    def __init__(self, config_name=None, **kwargs):
        if config_name != None:
            self.__dict__.update(get_config_as_dict('Acquisition', config_name))
        self.__dict__.update(kwargs)

    def getdata(self, shot, config_name=None, **kwargs):
        """Get the data and return prescribed subclass of BaseData.
        
        :param shot: shot number
        :param config_name: ?? bdb name of a fetcher class in the configuration file
        :returns: an instance of a subclass of \
        :py:class:`~pyfusion.data.base.BaseData` or \
        :py:class:`~pyfusion.data.base.BaseDataSet`

        This method needs to know which  data fetcher class to use, if a
        config_name      argument     is      supplied      then     the
        ``[Diagnostic:config_name]``   section   must   exist   in   the
        configuration   file  and   contain  a   ``data_fetcher``  class
        specification, for example::

         [Diagnostic:H1_mirnov_array_1_coil_1]
         data_fetcher = pyfusion.acquisition.H1.fetch.H1DataFetcher
         mds_path = \h1data::top.operations.mirnov:a14_14:input_1
         coords_cylindrical = 1.114, 0.7732, 0.355
         coord_transform = H1_mirnov

        If a ``data_fetcher`` keyword argument is supplied, it overrides
        the configuration file specification.

        The  fetcher  class  is  instantiated,  including  any  supplied
        keyword arguments, and the result of the ``fetch`` method of the
        fetcher class is returned.
        """
        from pyfusion import config
        # if there is a data_fetcher arg, use that, otherwise get from config
        if kwargs.has_key('data_fetcher'):
            fetcher_class_name = kwargs['data_fetcher']
        else:
            fetcher_class_name = config.pf_get('Diagnostic',
                                               config_name,
                                               'data_fetcher')
        fetcher_class = import_from_str(fetcher_class_name)
        d = fetcher_class(self, shot,
                             config_name=config_name, **kwargs).fetch()
        d.history += "\n:: shot: %d\n:: config: %s" %(shot, config_name)

        return d
        
class BaseDataFetcher(object):
    """Base  class  providing  interface   for  fetching  data  from  an
    experimental database.
    
    :param acq: in instance of a subclass of :py:class:`BaseAcquisition`
    :param shot: shot number
    :param config_name: name of a Diagnostic configuration section.
    
    It is expected that subclasses of BaseDataFetcher will be called via
    the :py:meth:`~BaseAcquisition.getdata` method, which calls the data
    fetcher's :py:meth:`fetch` method.
    """
    def __init__(self, acq, shot, config_name=None, **kwargs):
        self.shot = shot
        self.acq = acq
        if config_name != None:
            self.__dict__.update(get_config_as_dict('Diagnostic', config_name))
            if pyfusion.VERBOSE>3: print(get_config_as_dict('Diagnostic', config_name))
        self.__dict__.update(kwargs)
        self.config_name=config_name
#        print('BDFinit',config_name,self.__dict__.keys())

    def setup(self):
        """Called by :py:meth:`fetch` before retrieving the data."""
        pass
    def do_fetch(self):
        """Actually fetches  the data, using  the environment set  up by
        :py:meth:`setup`

        :returns: an instance of a subclass of \
        :py:class:`~pyfusion.data.base.BaseData` or \
        :py:class:`~pyfusion.data.base.BaseDataSet`

        Although :py:meth:`BaseDataFetcher.do_fetch` does not return any
        data object itself, it is expected that a `do_fetch()` method on
        a subclass of :py:class:`BaseDataFetcher` will.
        """
        pass
    def pulldown(self):
        """Called by :py:meth:`fetch` after retrieving the data."""
        pass
    def error_info(self, step=None):
        """ return specific information about error to aid interpretation - e.g for mds, path
        The dummy return should be replaced in the specific routines
        """
        return('(further info not provided by %s)' % (self.acq.acq_class))

    def fetch(self):
        """Always use  this to fetch the data,  so that :py:meth:`setup`
        and  :py:meth:`pulldown` are  used to  setup and  pull  down the
        environmet used by :py:meth:`do_fetch`.
        
        :returns: the instance of a subclass of \
        :py:class:`~pyfusion.data.base.BaseData` or \
        :py:class:`~pyfusion.data.base.BaseDataSet` returned by \
        :py:meth:`do_fetch`
        """        
        if pyfusion.DEBUG>3:
            exception = None  # defeat the try/except
        else: exception = Exception

        try:
            self.setup()
        except exception as details:
            raise LookupError("%s\n%s" % (self.error_info(step='setup'),details))
        try:
            data = self.do_fetch()
        except Exception as details:   # put None here to show exceptions.
                                       # then replace with Exection once
                                       # "error_info" is working well

            # this is to provide traceback from deep in a call stack
            # the normal traceback doesn't see past the base.py into whichever do_fetch
            # this simple method doesn't work, as it only has info after getting to the prompt
            if  hasattr(sys, "last_type"):traceback.print_last()
            else: print('sys has not recorded any exception - needs to be at prompt?')

            # this one DOES work.
            print(sys.exc_info())
            (extype, ex, tb) = sys.exc_info()
            for tbk in traceback.extract_tb(tb):
                print("Line {0}: {1}, {2}".format(tbk[1],tbk[0],tbk[2:]))
            raise LookupError("%s\n%s" % (self.error_info(step='do_fetch'),details))
        data.meta.update({'shot':self.shot})
        # Coords shouldn't be fetched for BaseData (they are required
        # for TimeSeries)
        #data.coords.load_from_config(**self.__dict__)
        self.pulldown()
        return data

class MultiChannelFetcher(BaseDataFetcher):
    """Fetch data from a diagnostic with multiple timeseries channels.

    This fetcher requres a multichannel configuration section such as::

     [Diagnostic:H1_mirnov_array_1]
     data_fetcher = pyfusion.acquisition.base.MultiChannelFetcher
     channel_1 = H1_mirnov_array_1_coil_1
     channel_2 = H1_mirnov_array_1_coil_2
     channel_3 = H1_mirnov_array_1_coil_3
     channel_4 = H1_mirnov_array_1_coil_4

    The channel  names must be  `channel\_` followed by an  integer, and
    the channel  values must correspond to  other configuration sections
    (for        example       ``[Diagnostic:H1_mirnov_array_1_coil_1]``,
    ``[Diagnostic:H1_mirnov_array_1_coil_1]``, etc)  which each return a
    single               channel               instance               of
    :py:class:`~pyfusion.data.timeseries.TimeseriesData`.
    """
    def ordered_channel_names(self):
        """Get an ordered list of the channel names in the diagnostic

        :rtype: list
        """
        channel_list = []
        for k in self.__dict__.keys():
            if k.startswith('channel_'):
                channel_list.append(
                    [int(k.split('channel_')[1]), self.__dict__[k]]
                    )
        channel_list.sort()
        return [i[1] for i in channel_list]
    
    def fetch(self):
        """Fetch each  channel and combine into  a multichannel instance
        of :py:class:`~pyfusion.data.timeseries.TimeseriesData`.

        :rtype: :py:class:`~pyfusion.data.timeseries.TimeseriesData`
        """
 
        ## initially, assume only single channel signals
        # this base debug breakpoint will apply to all flavours of acquisition
        debug_(pyfusion.DEBUG, level=2, key='base_multi_fetch')
        ordered_channel_names = self.ordered_channel_names()
        data_list = []
        channels = ChannelList()
        timebase = None
        meta_dict={}
        if hasattr(self, 't_min') and hasattr(self, 't_max'):
            t_range = [float(self.t_min), float(self.t_max)]
        else:
            t_range = []
        for chan in ordered_channel_names:
            sgn = 1
            if chan[0]=='-': sgn = -sgn
            bare_chan = (chan.split('-'))[-1]
            fetcher_class = import_setting('Diagnostic', bare_chan, 'data_fetcher')
            tmp_data = fetcher_class(self.acq, self.shot,
                                     config_name=bare_chan).fetch()

            if len(t_range) == 2:
                tmp_data = tmp_data.reduce_time(t_range)
            channels.append(tmp_data.channels)
            # two tricky things here - tmp.data.channels only gets one channel hhere
            #config_name for a channel is attached to the multi part -
            #we need to move it to the particular channel 
            # was  channels[-1].config_name = chan
            channels[-1].config_name = tmp_data.config_name
            meta_dict.update(tmp_data.meta)
            #print(tmp_data.signal[-1], sgn)
            tmp_data.signal = sgn * tmp_data.signal
            #print(tmp_data.signal[-1], sgn)
            if timebase == None:
                timebase = tmp_data.timebase
                data_list.append(tmp_data.signal)
            else:
                if hasattr(self, 'skip_timebase_check') and self.skip_timebase_check == 'true':
                    data_list.append(tmp_data.signal)
                else:
                    try:
                        assert_array_almost_equal(timebase, tmp_data.timebase)
                        data_list.append(tmp_data.signal)
                    except:
                        raise
        signal=Signal(data_list)
        output_data = TimeseriesData(signal=signal, timebase=timebase,
                                     channels=channels)
        #output_data.meta.update({'shot':self.shot})
        output_data.meta.update(meta_dict)
        return output_data

