"""
Module to create XML forms from templates with includes and color settings.

# Include definition in includes.xml:
#  <include name="header">
#    <param name="param-1">defaultvalue</param>
#    <definition>
#        ...content..
#    </definition>
#  </include>
#
# Include usage in form template:
#  <include content="header">
#       <param name="id" value="12" />
#  </include>

"""
import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import xbmc
import xbmcvfs
import xbmcaddon

class FormCreator:
    """
    Class to create XML forms from templates, processing includes and color settings.
    """
    XMLFORMSDIR = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')) + "resources/xmlforms/"
    def __init__(self):
        self.colors = {}
        self.includes = {}
        self.state = {}
        self.addon = xbmcaddon.Addon()
        self.statefile = xbmcvfs.translatePath(self.addon.getAddonInfo('profile')) + 'formstate.json'
        self.targetdir = xbmcvfs.translatePath(self.addon.getAddonInfo('path')) + 'resources/skins/Default/1080i/'
        self.__loadstate(self.statefile)

    def savestate(self, statefile):
        """
        Function to save the current state to a file.
        
        :param self: 
        :param statefile: state of conversion
        """
        Path(statefile).write_text(json.dumps(self.state), encoding='utf-8')

    def __loadstate(self, statefile):
        if Path(statefile).is_file():
            self.state = json.loads(Path(statefile).read_text(encoding='utf-8'))
        if self.state is None:
            self.state = {'skindir':xbmc.getSkinDir()}

    def __loadcolors(self):
        # Load colors from skin settings or a predefined dictionary
        tree = ET.parse(self.XMLFORMSDIR + 'defaultcolours.xml')

        root = tree.getroot() # name=colors

        self.colors = {}
        for color in root.findall('color'):
            name = color.get('name')
            value = color.text
            self.colors[name] = value

    def __load_includes(self):
        # Load include definitions from a predefined file
        tree = ET.parse(self.XMLFORMSDIR + "includes.xml")

        root = tree.getroot() # name=includes

        # Process includes
        includes = root.findall('include')
        for include in includes:
            includename = include.get('name')
            contentname = include.get('content')
            params = {param.get('name'): param.get('value') for param in include.findall('param')}
            definition = include.find('definition')
            self.includes.update({includename: (contentname, params, definition)})

    def processxml(self, formname: str):
        """
        Function to process the XML form template and generate the final XML form.
        Also includes color replacement based on skin settings.
        
        :param self:
        :param formname: The name of the form template to process.
        """
        self.__loadcolors()
        self.__load_includes()

        tree = ET.parse(self.XMLFORMSDIR + formname)
        root = tree.getroot()

        # Process includes, a form can only use includes defined in includesfile, it cannot define new includes itself

        # Create a parent map to find parents of elements
        parentMap = {c: p for p in tree.iter() for c in p}

        includes = root.findall('.//include')
        for useinclude in includes:
            parent = parentMap[useinclude]
            includename = useinclude.get('name')
            definedinclude = self.includes.get(includename)
            if definedinclude is None:
                continue
            newnode = copy.deepcopy(definedinclude[2])
            if newnode is None: # it is a new definition, ignore the one in includesfile
                raise RuntimeError("Include without definition")
            definedparams = definedinclude[1] # default params

            useincludeparams = {param.get('name'): param.get('value') for param in useinclude.findall('param')}
            # Replace parameters
            newnodetext:str = ET.tostring(newnode, encoding='utf-8').decode('utf-8')

            # A parameter used in the include can be either defined in the useinclude or in the definedinclude or both
            # If in definedinclude then that is the default value, overridden by useinclude if present
            # So we first set the values explicitly defined in useinclude, then the rest from definedinclude

            for elemid in useincludeparams.keys():
                newnodetext = newnodetext.replace(f'$PARAM[{elemid}]', useincludeparams[elemid])

            # Now for the explicitly defined ones there is no long '$PARAM[elemid]' in the text, 
            # so we only replace the remaining ones

            for elemid in definedparams.keys():
                newnodetext = newnodetext.replace(f'$PARAM[{elemid}]', definedparams[elemid])

            newnode = ET.fromstring(newnodetext)

            index = list(parent).index(useinclude)
            for subelem in newnode:
                index += 1
                parent.insert(index, subelem)
            parent.remove(useinclude)

        skindir = xbmc.getSkinDir()
        if skindir == 'skin.estuary': # No color changes needed, we build for estuary
            pass
        else:
            self.__skinrelatedprocessing(root, skindir)

        outputfile = self.targetdir + formname.replace('.xml.templ', '.xml')
        tree.write(outputfile, encoding='utf-8', xml_declaration=True)

    def __skinrelatedprocessing(self, root: ET.Element, skindir: str):
        self.state['skindir'] = skindir
#        skindir = 'skin.estuary'
        if skindir == 'skin.estuary': # fonts and params are set
            pass
        else:
            for elem in root.iter():
                if 'colordiffuse' in elem.attrib:
                    if elem.attrib['colordiffuse'] in self.colors:
                        elem.attrib['colordiffuse'] = self.colors[elem.attrib['colordiffuse']]
            for elem in root.iter('shadowcolor'):
                if elem.text in self.colors:
                    elem.text = self.colors[elem.text]
            for elem in root.iter('textcolor'):
                if elem.text in self.colors:
                    elem.text = self.colors[elem.text]
            for elem in root.iter('invalidcolor'):
                if elem.text in self.colors:
                    elem.text = self.colors[elem.text]
            for elem in root.iter('backgroundcolor'):
                if elem.text in self.colors:
                    elem.text = self.colors[elem.text]

    def __del__(self):
        self.savestate(self.statefile)

if __name__ == "__main__":
    forms = [
        'channels.xml.templ',
        'movies.xml.templ',
        'screen-epg.xml.templ',
        'recordings.xml.templ',
        'ziggohome.xml.templ',
        'sidewindow.xml.templ'
    ]
    fc = FormCreator()
    for form in forms:
        fc.processxml(FormCreator.XMLFORMSDIR + form)
        xbmc.log(f'Processed form {form}', xbmc.LOGDEBUG)
    fc.savestate(fc.statefile)
