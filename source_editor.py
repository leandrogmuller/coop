import base64
import codecs
import inspect
import operator
import os
import subprocess
import sys
import threading
import traceback
from operator import attrgetter

import jedi
import xml.dom.minidom
from yapf.yapflib.yapf_api import FormatCode

import kernel_profile
from dba.lang02 import Lang02
from dba.lang03 import Lang03
from dba.pkge import Pkge
from dba.srvr import Srvr
from dba.var03 import Var03
from kernel.actvs.SourceAction import SourceAction
from kernel.actvs.source_save import SourceSave
from kernel.actvs.util_names import ModuleUtil
from kernel.box.tr import ModuleBox
from kernel.db.session import getsession
from kernel.lang.tr import gettext
from kernel.obj.component import Button, DMessage, GridLayout, TextEditorSource, TextField, FinderDialog, \
    Tree, TreeRow, Label, TextMark, View, AutoCompleteDoc, ComboBox, \
    ComboBoxItem, DialogPanel, HBoxLayout, FormLayout, FormLayoutItem, Alignment, SplitPane, TreeRows, Tab, BaseLayout
from kernel.obj.dialog import MessageDialog, Message
from kernel.obj.instance import Window, R
from kernel.obj.type import KeyCode
from kernel.root.route_process import RouteWorkProcess
from kernel.sys import Compare
from kernel.util.text import TextUtil
from kernel.exceptions import AlertException


class ViewEditor(Window):
    def __init__(self):
        super().__init__(self)
        self.check_source_bk = False
        self.target_module = ""
        self.target_class = ""
        self.textEditor: TextEditorSource = self.R.get_obj("text_editor")
        self.xml_editor: TextEditorSource = self.R.get_obj("xml_editor")
        self.viewEditor: View = self.R.get_obj("editor")

        # self.viewEditor.alignment.clear()

        self.grid_root: GridLayout = self.R.get_obj("grid_root")
        self.grid_root.setRowStretch(1, 1)

        self.source_save = ""
        self.xml_save = ""

        self.old_text_tree = ""
        self.calc_def_class = ""
        self.view_create()
        self.panelLeft = None
        self.panelRigth = None
        self.srvr: Srvr = None

        self.list_class = list()
        self.scAction = SourceAction()
        self.source_history = []
        self.source_index = -1
        self.temp_files = []

    def view_create(self):
        self.view = self.R.get_obj("view1")
        self.module: TextField = self.R.get_obj("module")
        self.pkge: TextField = self.R.get_obj("pkge")
        self.lb_module: TextField = self.R.get_obj("lb_module")
        self.desc: TextField = self.R.get_obj("desc")
        self.cb_viewxml: ComboBox = self.R.get_obj("cb_viewxml")
        self.lb_status: TextField = self.R.get_obj("lb_status")
        self.lb_version: TextField = self.R.get_obj("lb_version")
        self.bt_ative: Button = self.R.get_obj("bt_ative")
        self.bt_save: Button = self.R.get_obj("bt_save")
        self.bt_check_py: Button = self.R.get_obj("bt_check_py")
        self.bt_organ_py: Button = self.R.get_obj("bt_organ_py")

        self.bt_check_xml: Button = self.R.get_obj("bt_check_xml")
        self.bt_organ_xml: Button = self.R.get_obj("bt_organ_xml")
        self.table_log_py: Tree = self.R.get_obj("table_log_py")
        self.table_log_xml: Tree = self.R.get_obj("table_log_xml")
        self.pop_new_module: DialogPanel = self.R.get_obj("dia_detail")
        self.dialog_detail: DialogPanel = self.R.get_obj("dialog_detail")
        self.splitSource: SplitPane = self.R.get_obj("splitSource")
        self.splitLog: SplitPane = self.R.get_obj("splitLog")

        self.tree: Tree = self.R.get_obj("treeSource")
        self.cb_preview: ComboBox = self.R.get_obj("cb_preview")
        self.cb_preview._list_views = {}
        self.grid_preview: GridLayout = self.R.get_obj("grid_preview")

        self.btNovo = self.R.get_obj("btNovo")
        self.set_focus(self.pkge)
        self.go_to_view(self.view)
        self.text_source_check = ""
        self.repository_preview = None

        session = getsession()

        try:
            self.sizes_wight = [200, 500]
            self.sizes_height = [500, 100]
            query = session.query(Var03).filter(
                Var03.varid.ilike('scsp%'),
                Var03.user == str(self.sy.user)).all()
            for q in query:
                if q.value == 'None':
                    q.value = 10
                if q.varid == 'scspw1':
                    self.sizes_wight[0] = int(q.value)
                if q.varid == 'scspw2':
                    self.sizes_wight[1] = int(q.value)
                if q.varid == 'scsph1':
                    self.sizes_height[0] = int(q.value)
                if q.varid == 'scsph2':
                    self.sizes_height[1] = int(q.value)

            self.splitSource.sizes = self.sizes_wight
            self.splitLog.sizes = self.sizes_height

        except:
            traceback.print_exc()
        finally:
            session.close()

    def set_views_combox(self):
        try:
            import xml.etree.cElementTree as ET
            views = ET.fromstring(self.xml_editor.text)
            val_key = self.cb_preview.key_select
            self.cb_preview.items.clear()

            self.repository_preview = R()
            self.get_child(views, None, self.repository_preview)
            self.grid_preview.clear()
            self.grid_preview.reload()
            self.cb_preview._list_views = {}
            for idx, key in enumerate(self.repository_preview.objects,
                                      start=0):
                obj = self.repository_preview.get_obj(key)
                for att in obj.__dict__.keys():
                    if inspect.ismethod(getattr(obj, att)):
                        setattr(obj, att, None)
                    if att == "module_searsh":
                        setattr(obj, "module_searsh", None)
                    if att == "class_searsh":
                        setattr(obj, "class_searsh", None)
                    if att == "searsh_key":
                        setattr(obj, "searsh_key", None)
                if Compare.isinstance(obj, View):
                    id_ = obj.id
                    self.cb_preview._list_views[id_] = []
                    for item in list(obj):
                        self.cb_preview._list_views[id_].append(item)
                        obj.remove(item)
                    item = ComboBoxItem(id_, id_)
                    self.cb_preview.items.append(item)
                    if idx == 0:
                        self.cb_preview.key_select = id_

                if Compare.isinstance(obj, DialogPanel):
                    id_ = obj.id
                    self.cb_preview._list_views[id_] = []
                    for item in list(obj):
                        self.cb_preview._list_views[id_].append(item)
                        obj.remove(item)
                    item = ComboBoxItem(id_, id_)
                    self.cb_preview.items.append(item)
                    if idx == 0:
                        self.cb_preview.key_select = id_

            self.cb_preview.key_select = val_key
            self.select_combo_view()


        except:
            traceback.print_exc()
            exc_type, exc_value, exc_traceback = sys.exc_info()  # pylint: disable=W0612
            self.alert_bar = DMessage("W", "kernel.lang.dev.028",
                                      str(exc_value))

    def select_combo_view(self):
        key = self.cb_preview.key_select
        height_ = None
        if key in self.repository_preview.objects:
            type = self.repository_preview.objects[key]
            if Compare.isinstance(type, DialogPanel):
                self.grid_preview.alignment.clear()
                self.grid_preview.alignment.append(Alignment.AlignLeft)
                self.grid_preview.alignment.append(Alignment.AlignAbsolute)
                self.grid_preview.alignment.append(Alignment.AlignTop)
                if hasattr(type, "height"):
                    height_ = type.height
            else:
                self.grid_preview.style = ""
                self.grid_preview.alignment.clear()

        if key in self.cb_preview._list_views:
            items = self.cb_preview._list_views[key]
            self.grid_preview.clear()
            if len(items) == 0:
                return
            for idx, item in enumerate(items):
                if idx == 0 and Compare.isinstance(item, BaseLayout):
                    item.style = "#%s{border:1px solid black;}" % item.id
                self.grid_preview.append(item)
            self.grid_preview.height = height_

            self.grid_preview.reload()

    def edit_source_action(self):

        if self.textEditor.editable == True:
            if self.source_save != self.textEditor.text or self.xml_save != self.xml_editor.text:
                msg1 = gettext("kernel.lang.dev.save")
                msg2 = gettext("kernel.lang.dev.notsave")
                msg3 = gettext("kernel.lang.dev.cancel")
                msg = gettext("kernel.lang.dev.021")
                dia = MessageDialog(self)
                dia.set_message(msg, msg1, self.res_save, msg2,
                                self.res_not_save, msg3, self.res_cancel)

            else:
                self.edit_view(False)
        else:
            self.edit_source_call(self.pkge_active, self.module_active)

    def res_cancel(self):
        pass

    def res_save(self):
        self.save_source()
        self.edit_view(False)

    def res_not_save(self):
        self.textEditor.text = self.source_save
        self.xml_editor.text = self.xml_save
        self.edit_view(False)

    def append_history(self, type, position=0, editable=False):
        if len(self.source_history) > (self.source_index + 1):
            del self.source_history[self.source_index + 1:]

        history = {}
        history["module"] = self.module_active
        history["pkge"] = self.pkge_active
        history["type"] = type
        history["position"] = position
        history["editable"] = editable
        self.source_history.append(history)
        self.source_index = len(self.source_history) - 1
        self.check_history_source()

    def view_source(self):
        self.source_history.clear()
        self.source_index = -1
        self.view_source_call(self.pkge.text, self.module.text)
        if self.alert_bar is None:
            self.append_history("file")

    def view_source_call(self, pkge, module):

        self.srvr = self.scAction.get_source(pkge, module)
        if self.srvr is None:
            raise AlertException('E', "kernel.lang.dev.006", module, pkge)
        else:
            self.module_active = module
            self.pkge_active = pkge
            self.__create_view_source()
            self.check_tree()
            self.set_value_temp()

        self.edit_view(False)

    def create_module(self):
        self.source_history.clear()
        self.source_index = -1
        self.module_active = self.module.text
        self.pkge_active = self.pkge.text
        session = getsession()
        tl_pkge: Pkge = session.query(Pkge).get(self.pkge_active)

        if tl_pkge is None:
            raise AlertException('E', "kernel.lang.dev.023")

        tl_mod = self.scAction.get_source(self.pkge_active, self.module_active)
        if not tl_mod is None:
            raise AlertException('E', "kernel.lang.dev.001")

        if self.module_active == "":
            raise AlertException('E', "kernel.lang.dev.002")

        if self.pkge_active == "":
            raise AlertException('E', "kernel.lang.dev.005")

        self.R.get_obj('desc').editable = True
        self.R.get_obj('desc').text = ''
        self.R.get_obj('cb_viewxml').key_select = 'False'
        self.R.get_obj('cb_viewxml').editable = True
        self.R.get_obj('bt_save_prop').editable = True
        self.R.get_obj('bt_save_prop').action = self.create_module2
        self.R.get_obj('bt_cancel_prop').action = self.cancel_prop
        self.pop_new_module.show()

    def cancel_prop(self):
        self.pop_new_module.close()
        self.R.get_obj('bt_cancel_prop').action = self.cancel_properties
        self.R.get_obj('bt_save_prop').action = self.save_properties

    def create_module2(self):
        self.pop_new_module.close()
        self.R.get_obj('bt_cancel_prop').action = self.cancel_properties
        self.R.get_obj('bt_save_prop').action = self.save_properties
        self.textEditor.text = ""
        self.xml_editor.text = ""
        self.lb_module.text = self.pkge_active + "." + self.module_active

        self.set_value_temp()

        if self.cb_viewxml.key_select == 'True':
            self.xml_editor.text = "<Views>\n<View id=\"view_" + self.lb_module.text + "\">\n</View>\n</Views>"
        else:
            self.xml_editor.text
        self.table_log_py.rows.clear()
        self.tree.rows.clear()
        self.go_to_view(self.viewEditor)
        self.append_history("file")
        self.edit_view(True)
        self.lb_status.text = "Inactive"
        self.lb_version.text = "1"
        self.bt_ative.image = "kernel.img.dev.inactive"
        self.textEditor.list_text_mark.clear()
        self.xml_editor.list_text_mark.clear()
        self.srvr = Srvr()
        self.srvr.xml_view = eval(self.R.get_obj('cb_viewxml').key_select)
        self.srvr.desc = self.R.get_obj('desc').text

    def set_value_temp(self):
        self.source_save = self.textEditor.text
        self.xml_save = self.xml_editor.text

    def edit_source(self):
        self.source_history.clear()
        self.source_index = -1
        self.edit_source_call(self.pkge.text, self.module.text)
        if self.alert_bar is None:
            self.append_history("file", 0, True)

    def edit_source_call(self, pkge, module):
        self.repository_preview = R()
        self.module_active = module
        self.pkge_active = pkge
        self.srvr = self.scAction.get_source(self.pkge_active,
                                             self.module_active)

        if self.srvr is None:
            msg = DMessage()
            msg.type = DMessage.ERROR
            if self.module_active is None:
                self.module_active = ""
            msg.code = "kernel.lang.dev.005"
            msg.element1 = self.module_active
            msg.element2 = self.pkge_active  # not found module in pkge
            self.alert_bar = msg
        else:
            self.table_log_py.rows = TreeRows()
            self.tree.rows = TreeRows()
            self.__create_view_source()
            self.edit_view(True)
            self.set_value_temp()
            self.check_tree()
            # self.check_source_background(self.textEditor)
            # self.check_source_xml(self.xml_editor)
            # self.check_source(self.textEditor)

    def __create_view_source(self):
        self.old_text_tree = ""
        self.calc_def_class = ""

        self.lb_module.text = self.pkge_active + "." + self.module_active
        self.desc.text = self.srvr.desc
        self.cb_viewxml.key_select = str(self.srvr.xml_view)
        if self.srvr.source is not None:
            try:
                self.textEditor.text = self.decode_base64(self.srvr.source)
            except:
                traceback.print_exc()
                self.xml_editor.text = ""
        else:
            self.textEditor.text = ""
        if self.srvr.xml is not None:
            try:
                self.xml_editor.text = self.decode_base64(self.srvr.xml)
            except:
                self.xml_editor.text = ""
        else:
            self.xml_editor.text = ""
        self.lb_version.text = self.srvr.version
        self.textEditor.list_text_mark.clear()
        self.xml_editor.list_text_mark.clear()

        if self.srvr.active == True:
            self.lb_status.text = "Active"
            self.bt_ative.image = "kernel.img.dev.active"
        else:
            self.lb_status.text = "Inactive"
            self.bt_ative.image = "kernel.img.dev.inactive"

        self.panel_central: GridLayout = self.R.get_obj("panel_central")

        self.table_log_py.rows = TreeRows()
        self.tree.rows = TreeRows()

        self.mark_debug()
        self.set_focus(self.desc)
        self.go_to_view(self.viewEditor)
        self.refresh()

    def edit_view(self, status: bool):
        self.grid_preview.clear()
        self.cb_preview.items.clear()
        self.repository_preview = R()
        self.textEditor.editable = status
        self.xml_editor.editable = status
        self.desc.editable = status
        self.textEditor.list_source_validator = list()

        self.bt_ative.enabled = status
        self.bt_save.enabled = status
        self.bt_check_py.enabled = status
        self.bt_organ_py.enabled = status
        self.bt_check_xml.enabled = status
        self.bt_organ_xml.enabled = status
        self.R.get_obj("menu_save").enabled = status
        self.R.get_obj("menu_py_org").enabled = status
        self.R.get_obj("menu_xml_org").enabled = status
        self.R.get_obj("menu_active").enabled = status

        if status:
            self.desc.style = "background-color: #FFFFFF;"
            self.textEditor.style = "background-color: #FFFFFF;"
            self.xml_editor.style = "background-color: #FFFFFF;"
        else:
            self.desc.style = "background-color: #E0E0E0;"
            self.textEditor.style = "background-color: #E0E0E0;"
            self.xml_editor.style = "background-color: #E0E0E0;"

        if status:
            self.bt_save.image = "kernel.img.dev.save"
            self.bt_check_py.image = "kernel.img.dev.check_source"

    def keypress_editor(self, keypress, obj):
        if keypress == (KeyCode.Key_Control, KeyCode.Key_S):
            self.save_source()

        if keypress in [KeyCode.Key_Enter, KeyCode.Key_Return]:
            self.refresh()

    def go_to_line(self):
        obj = None
        if self.get_focus() == self.textEditor:
            obj = self.textEditor

        if self.get_focus() == self.xml_editor:
            obj = self.xml_editor
        if obj is None:
            return
        self.dialog_line = DialogPanel()
        self.get_current_view().append(self.dialog_line)
        panel = FormLayout()
        self.dialog_line.append(panel)
        self.dialog_line.modal = True
        itemf = FormLayoutItem()
        label = Label()
        itemf.label = label
        label.text = gettext("kernel.lang.dev.047")
        text_line = TextField()
        self.dialog_line.field = text_line
        text_line.obj = obj
        text_line.event_press = self.go_line_key
        text_line.event_press_key.append(KeyCode.Key_Enter)
        text_line.event_press_key.append(KeyCode.Key_Return)
        text_line.event_press_key.append(KeyCode.Key_Escape)
        self.set_focus(text_line)
        itemf.component = text_line
        panel.append(itemf)
        button = Button()
        button.text = gettext("ok")
        button.action = self.go_line
        itemf = FormLayoutItem()
        itemf.component = button
        panel.append(itemf)

        self.dialog_line.show()

    def go_line_key(self, keypress, obj):
        if keypress in [KeyCode.Key_Enter, KeyCode.Key_Return]:
            self.go_line()
        if keypress == KeyCode.Key_Escape:
            self.dialog_line.close()

    def go_line(self):
        lines = str(self.dialog_line.field.text).split(":")
        self.dialog_line.close()
        line = 0
        col = 0
        try:
            for idx, pos in enumerate(lines, start=0):
                if idx == 0:
                    line = int(pos)
                if idx == 1:
                    col = int(pos)

            if line > 0:
                pos = TextUtil.get_position(self.dialog_line.field.obj.text,
                                            line, col)
                self.dialog_line.field.obj.cursor_position.position = pos
        except:
            traceback.print_exc()

    def mark_debug(self):
        tr = threading.current_thread()
        self.textEditor.debug_lines.clear()

        list_debug = RouteWorkProcess.get_all_debug(tr.rp.session_login)
        for conf_debug in list_debug:
            pkge, module = ModuleUtil.get_file_to_module(conf_debug["file"])
            if pkge == self.pkge_active and module == self.module_active:
                self.textEditor.debug_lines.append(int(conf_debug["line"]))

    def bt_check_source(self):
        self.check_source(self.textEditor)

    def bt_check_source_xml(self):
        self.check_source_xml(self.xml_editor)

    def decode_base64(self, value):
        return str(base64.b64decode(value), "utf-8")

    def encode_base64(self, value):
        v = base64.b64encode(str(value).encode("utf-8"))
        return v.decode()

    def check_source_xml(self, obj: TextEditorSource):
        self.table_log_xml.rows = TreeRows()

        source = obj.text
        try:
            xml.dom.minidom.parseString(source)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()  # pylint: disable=W0612
            row = TreeRow()
            row["code"] = "999"
            row["log"] = str(exc_value)
            row["type"] = "E"
            self.table_log_xml.rows.append(row)
            lbType = Label()
            lbType.text = row["code"]
            lbType.style = "color:red"
            row.components["code"] = lbType

    def check_tree(self):
        text = self.textEditor.text

        if self.old_text_tree == text and self.old_text_tree != "":
            return
        self.old_text_tree = text

        lines_tree = []
        lines = text.split('\n')
        try:
            p = {}
            for il, l1 in enumerate(lines):
                p[il] = []
                for ix, a in enumerate(l1):
                    if a != " " and len(p[il]) == 0:
                        p[il].append(ix)
                    elif len(p[il]) > 0 and a in [" ", ":", "."]:
                        p[il].append(ix)
                        break
                if len(p[il]) == 1:
                    p[il].append(len(l1) - 1)

            lines1 = list(p.keys())
            u = -1
            for l in lines1:
                added = False
                if len(p[l]) == 0:
                    continue
                if u > l:
                    continue
                col1 = p[l][0]
                col2 = p[l][1]
                word = lines[l][col1:col2]
                column_start = col1
                if len(word) > 0:
                    if word in ["class", "def"]:
                        tree_temp = {}
                        tree_temp["type"] = word
                        tree_temp["line"] = l
                        tree_temp["childs"] = []
                        tree_temp["method"] = ""
                        tree_temp["position"] = (l, col1)
                        pz = []
                        for ip, a in enumerate(lines[l][col2:]):
                            if a != " " and len(pz) == 0:
                                pz.append(col2 + ip)
                            elif len(pz) > 0 and a in [" ", ":", "(", "\n"]:
                                pz.append(col2 + ip)
                                break
                        if len(pz) == 2:
                            tree_temp["method"] = lines[l][pz[0]:pz[1]]
                        tree_temp["name"] = "%s %s" % (tree_temp["type"], tree_temp["method"])
                        lines_tree.append(tree_temp)
                        for u in lines1[l + 1:]:
                            if len(p[u]) == 0:
                                continue
                            col1 = p[u][0]
                            col2 = p[u][1]
                            column_end = col1
                            word1 = lines[u][col1:col2]
                            if word1 != "" and column_end > column_start:
                                if word1 in ["class", "def"]:
                                    child = {}
                                    child["type"] = word1
                                    child["line"] = u
                                    child["childs"] = []
                                    child["method"] = ""
                                    tree_temp["childs"].append(child)
                                    child["position"] = (u, col1)
                                    pz = []
                                    for ip, a in enumerate(lines[u][col2:]):
                                        if a != " " and len(pz) == 0:
                                            pz.append(col2 + ip)
                                        elif len(pz) > 0 and a in [" ", ":", "(", "\n"]:
                                            pz.append(col2 + ip)
                                            break
                                    if len(pz) == 2:
                                        child["method"] = lines[u][pz[0]:pz[1]]
                                    child["name"] = "%s %s" % (child["type"], child["method"])
                            elif column_end <= column_start:
                                if word1 in ["class", "def"]:
                                    break

                        tree_temp["childs"] = sorted(tree_temp["childs"], key=lambda i: i['method'])
            lines_tree = sorted(lines_tree, key=lambda i: i['method'])

            def create_child(rows: TreeRows, i, item, list_):
                treeRow = TreeRow()
                treeRow["method"] = item["name"]
                treeRow["type"] = item["type"]
                treeRow["method_name"] = item["method"]
                treeRow.position = item["position"]
                treeRow.expand = True
                rows.insert(i, treeRow)
                for z, child in enumerate(item["childs"]):
                    create_child(treeRow.childs, z, child, list_)

            def valid_tree(list_, tree):
                if isinstance(tree, Tree):
                    rows = tree.rows
                if isinstance(tree, TreeRow):
                    rows = tree.childs
                i = 0
                for i, item in enumerate(list_):
                    if len(rows) > i:
                        row1 = rows[i]
                        p = -1
                        insert = False
                        for z, row in enumerate(rows[i:]):
                            if row["method"] == item["name"]:
                                row.position = item["position"]
                                p = i + z
                                break
                            else:
                                for u, it in enumerate(list_[i:]):
                                    if row["method"] == it["name"]:
                                        row.position = item["position"]
                                        p = i + z
                                        if u > 0:
                                            insert = True
                                        break
                                if p > -1:
                                    break
                        if p > i:
                            lst = rows[i:p]
                            for r in lst:
                                rows.remove(r)
                            if insert:
                                create_child(rows, i, item, list_)
                        else:
                            if p < i:
                                rows.remove(rows[i])
                            if row1["method"] == item["name"]:
                                valid_tree(item["childs"], row1)
                            else:
                                create_child(rows, i, item, list_)


                    else:
                        create_child(rows, i, item, list_)
                if len(rows) > i + 1:
                    for row in list(rows[i + 1:]):
                        rows.remove(row)

            valid_tree(lines_tree, self.tree)

        except:
            traceback.print_exc()

    def event_on_click_tree(self, obj):

        for objz in obj.get_selected():
            if objz.position is not None:
                self.textEditor.cursor_position.set_position(objz.position[0] + 1, objz.position[1])
                self.append_history("line", self.textEditor.cursor_position.position,
                                    self.textEditor.editable)

                self.set_focus(self.textEditor)

    def go_line_source(self, obj):

        for objz in obj.get_selected():
            if objz["line"] is not None:
                position = TextUtil.get_position(self.textEditor.text,
                                                 objz["line"], objz["col"])
                self.textEditor.cursor_position.position = position
                self.set_focus(self.textEditor)

    def check_code(self, obj: TextEditorSource):
        self.check_tree()
        self.check_source(obj)

    def run_module(self):
        active = True
        if self.lb_status.text != "Active":
            active = False
        if self.source_save != self.textEditor.text or self.xml_save != self.xml_editor.text:
            active = False

        if active is False:
            msg = Message(self)
            msg.set_message('kernel.lang.dev.034', 'kernel.lang.dev.alert')
            btdel = Button()
            btdel.text = gettext('kernel.lang.dev.ok')
            # btdel.action = self.delete_domain_confirm
            msg.add_button(btdel)
            msg.set_icon_type(Message.IconType.Warning)
            msg.show()
        else:
            self.check_debug()
            list_class = []
            for child in self.tree.rows:
                if child["type"] == "class":
                    name = child["method_name"]
                    pos1 = TextUtil.get_position(self.textEditor.text, child.position[0], child.position[1])
                    pos = {"name": name, "pos": pos1}
                    list_class.append(pos)

            if len(list_class) == 1:
                cl = list_class[0]
                self.run_class_name(cl["name"], cl["pos"])
            elif len(list_class) > 0:
                self.dialog_line = DialogPanel()
                self.get_current_view().append(self.dialog_line)
                panel = GridLayout()
                self.dialog_line.append(panel)
                self.dialog_line.modal = True
                label = Label()
                label.text = gettext("kernel.lang.dev.035")
                label.column = 0
                label.row = 0
                panel.append(label)
                self.combo_run_class = ComboBox()
                self.combo_run_class.column = 0
                self.combo_run_class.row = 1
                for idx, objx in enumerate(list_class, start=0):
                    if idx == 0:
                        self.combo_run_class.key_select = objx["name"]
                    self.combo_run_class.items.append(
                        ComboBoxItem(objx["name"], objx["name"]))
                panel.append(self.combo_run_class)

                panelb = HBoxLayout()
                panel.append(panelb)
                panelb.alignment.append(Alignment.AlignLeft)
                panelb.column = 0
                panelb.row = 2

                btexec = Button()
                btexec.text = gettext("kernel.lang.dev.exec")
                btexec.action = self.run_class_module

                panelb.append(btexec)

                btcancel = Button()
                btcancel.text = gettext("kernel.lang.dev.cancel")
                btcancel.action = self.cancel_dia_class_module
                panelb.append(btcancel)
                self.dialog_line.show()
            else:
                self.alert_bar = DMessage("W", "kernel.lang.dev.043")

    def cancel_dia_class_module(self):
        self.dialog_line.close()

    def run_class_module(self):
        self.dialog_line.close()

        key = self.combo_run_class.key_select
        if key == ("", None):
            msg = Message(self)
            msg.set_message('kernel.lang.dev.034', 'kernel.lang.dev.alert')
            btdel = Button()
            btdel.text = gettext('kernel.lang.dev.ok')
            # btdel.action = self.delete_domain_confirm
            msg.add_button(btdel)
            msg.set_icon_type(Message.IconType.Warning)
            msg.show()
        pos = 0
        for child in self.tree.rows:
            if child["type"] == "class" and child["method_name"] == key:
                pos = TextUtil.get_position(self.textEditor.text, child.position[0], child.position[1])
                break
        self.run_class_name(key, pos)

    def run_class_name(self, class_name, pos):
        is_view = False
        if hasattr(self, "dialog_line"):
            self.dialog_line.close()
        if pos > 0:
            text = self.textEditor.text
            text = text[pos + 1:]

            c = 0
            for idx, i in enumerate(text, start=0):
                if i == "\n":
                    c = idx
                    break
            if c > 0:
                text = text[0:c]
                text = text.replace(" ", "")
                if text.find("(Window)") >= 0:
                    is_view = True

        if is_view:
            module = self.pkge_active + "." + self.module_active
            self.go_to_class(module, class_name, True)
        else:
            raise AlertException('E', 'kernel.lang.dev.109')

    def save_temp_file(self, source):
        import hashlib
        id_ = hashlib.md5(str(self.module_active).encode("UTF8")).hexdigest()
        path = kernel_profile.SY_BASE_DIR + "/temp/files/tempxy_" + self.module_active + str(
            id_) + ".py"
        self.temp_files.append(path)

        filenamez = os.path.abspath(path)
        file = codecs.open(filenamez, 'w', 'utf-8')
        for linez in source.splitlines():
            sz = linez + "\n"
            file.write(sz)

        file.close()
        return filenamez

    def remove_file_pth(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
        except:
            traceback.print_exc()

    def remove_file(self):
        for filenamez in self.temp_files:
            try:

                if os.path.exists(filenamez):
                    os.remove(filenamez)
            except:
                traceback.print_exc()

    def close_event(self):
        self.remove_file()
        self.close_instance()

    def kill_on_timeout(self, done, timeout, proc):
        if not done.wait(timeout):
            proc.kill()

    def check_source(self, obj: TextEditorSource):

        try:

            # import fast  # pylint: disable=E0611,E0401
            # fast.sys_removetrace(self.sy.id_wp)  # pylint: disable=E0401
            self.mark_debug()
            source = obj.text
            filenamez = self.save_temp_file(source)
            import multiprocessing
            num_cpus = multiprocessing.cpu_count()
            pylintset = kernel_profile.SY_BASE_DIR + "/.pylintrc"
            disable = ""
            if len(kernel_profile.PYLINT_DISABLE) > 0:
                disable = "--disable=%s" % (",".join(kernel_profile.PYLINT_DISABLE))
            vars = " %s  --load-plugins=pylint_django  --msg-template=\"{abspath}:{line:1d}:{column}: {msg_id}: {msg}\" --output-format=parseable " % disable
            comm = "python  -m pylint --rcfile  %s %s %s " % (pylintset, vars, filenamez)

            p = subprocess.Popen(comm,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True,
                                 cwd=None)
            # done = Event()
            # watcher = Thread(target=self.kill_on_timeout, args=(done, 60, p))
            # watcher.daemon = True
            # watcher.start()
            (out, err) = p.communicate('y')  # pylint: disable=W0612
            # done.set()
            vv = str(out, "utf-8")
            list_ = vv.split("\n")
            self.remove_file_pth(filenamez)
            self.table_log_py.rows.clear()
            list_text_mark = []
            tm = len(filenamez)
            ck_help = False
            las_row = None
            stopx = False
            lst_w = []
            lst_e = []
            lst_c = []
            has_error = False
            for log in list_:

                if str(log) == "":
                    stopx = True
                    continue

                if stopx:
                    continue
                log = log[tm:]
                if log == "":
                    continue
                t2 = log.find(":")
                z = log[0:t2]
                if filenamez.find(z) >= 0:
                    ck_help = True
                    t2 = log.find(":")
                    t1 = log[t2 + 1:]
                    t2 = t1.find(":")
                    line = t1[0:t2]
                    t1 = t1[t2 + 1:]
                    t2 = t1.find(":")
                    col = t1[0:t2]
                    t1 = t1[t2 + 2:]
                    t2 = t1.find(":")
                    code = t1[0:t2]
                    message = t1[t2 + 2:]
                    row = TreeRow()
                    try:
                        line = int(line)
                    except:
                        pass
                    try:
                        col = int(col)
                    except:
                        pass

                    row["pos"] = str(line) + ":" + str(col)
                    row["col"] = col
                    row["line"] = line
                    row["log"] = message

                    las_row = row

                    type_log = code[0]
                    row["codez"] = code
                    sc_type = "W"
                    if type_log == "C":
                        lst_c.append(row)
                        sc_type = "W"
                    if type_log == "R":
                        lst_w.append(row)
                        sc_type = "W"
                    if type_log == "W":
                        lst_w.append(row)
                        sc_type = "W"
                    if type_log == "E":
                        lst_e.append(row)
                        sc_type = "E"
                    if type_log == "F":
                        lst_e.append(row)
                        sc_type = "E"
                    if sc_type == "E":
                        has_error = True
                    row["type"] = type_log

                    sc = {}
                    list_text_mark.append(sc)
                    sc["type"] = sc_type
                    sc["line"] = line
                    sc["col"] = col
                    sc["params"] = list()

                    if code == 'W0611':
                        p1 = message.find('imported from')
                        if p1 > 8:
                            sc["params"] = [message[7:p1 - 1]]
                            continue

                    n = False
                    tx = ""
                    for t in message:
                        if t == "'" and n is False:
                            n = True
                            continue

                        if t == "'" and n:
                            n = False
                            sc["params"].append(tx)
                            tx = ""
                            continue
                        if n:
                            tx += t
                    tx = ""
                    n = False
                    for t in message:
                        if t == "(" and n is False:
                            n = True
                            continue

                        if t == ")" and n:
                            n = False
                            if tx.find('.') > -1:
                                tu = tx.split('.')
                                for tu1 in tu:
                                    sc["params"].append(tu1)
                            else:
                                sc["params"].append(tx)
                            tx = ""
                            continue
                        if n:
                            tx += t
                    # sc.params[

                elif ck_help:
                    dt = TreeRow()
                    dt["log"] = log
                    las_row.childs.append(dt)

            if has_error is False:
                self.text_source_check = source
            else:
                self.text_source_check = ""

            lst_e.sort(key=operator.itemgetter('line'))
            lst_w.sort(key=operator.itemgetter('line'))
            lst_c.sort(key=operator.itemgetter('line'))

            self.table_log_py.rows.extend(lst_e)
            self.table_log_py.rows.extend(lst_w)
            self.table_log_py.rows.extend(lst_c)
            for row in self.table_log_py.rows:

                lbType = Label()
                lbType.text = row["codez"]
                if row["type"] == "C":
                    lbType.style = "color:green"
                if row["type"] == "R":
                    lbType.style = "color:orange"
                if row["type"] == "W":
                    lbType.style = "color:orange"
                if row["type"] == "E":
                    lbType.style = "color:red"
                if row["type"] == "F":
                    lbType.style = "color:red"
                row.components["code"] = lbType

            self.check_tree()
            self.mark_workds(list_text_mark)
        except:
            traceback.print_exc()

    def check_source_flake(self, obj: TextEditorSource):
        try:

            list_err = ["F402", "F403", "F404", "F405", "F811", "F812", "F821", "F822", "F823", "F831", "X101", "X102",
                        "X103", "X104", "E999"]
            source = obj.text
            filenamez = self.save_temp_file(source)

            pathfrank = str(sys.prefix) + "/Scripts/flake8.exe"

            if os.name != 'nt':
                pathfrank = "flake8"  # --ignore=E3,E1,E2,E3,E4,E5,E6,E7,E8,W2 "

            if os.path.exists(pathfrank):
                pathfrank = pathfrank + " --ignore=E3,E1,E2,E3,E4,E5,E6,E7,E8,W2 "
            else:
                pathfrank = "python -m flake8 --ignore=E3,E1,E2,E3,E4,E5,E6,E7,E8,W2 "

            comm = pathfrank + filenamez
            p = subprocess.Popen(comm, env=os.environ,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True,
                                 cwd=None)

            (out, err) = p.communicate('y')  # pylint: disable=W0612
            vv = str(out, "utf-8")
            self.remove_file_pth(filenamez)
            list_ = vv.split("\r\n")
            self.table_log_py.rows = TreeRows()

            c = 0

            list_text_mark = []
            tm = len(filenamez)
            ck_help = False
            las_row = None
            stopx = False
            lst_w = []
            lst_e = []
            has_error = False
            for log in list_:
                # if c == 0:
                #     c = 1
                #     continue

                if os.name == 'nt':
                    p1 = log.find(":") + 1
                    log = log[p1:]

                if str(log) == "":
                    stopx = True
                    continue

                if log.find(":") == -1:
                    continue

                p1 = log.find(":") + 1
                v1 = log[p1:]
                p2 = v1.find(":")
                line = int(v1[:p2])
                v2 = v1[p2 + 1:]
                p3 = v2.find(":")
                col = int(v2[:p3])
                v3 = v2[p3 + 2:]
                p4 = v3.find(" ")
                code = v3[:p4]
                v4 = v3[p4 + 1:]
                message = v4
                message = message.replace("\\", "")

                # p5 = message.find("'")
                # var1 = message[p5 + 1:]
                # p6 = var1.find("'")
                # param = ""
                # if p6 != -1:
                #     var2 = var1[:p6]
                #     param = var2

                row = TreeRow()
                sc_type = "W"

                if code in list_err:
                    sc_type = "E"
                    has_error = True

                if sc_type == "W":
                    lst_w.append(row)
                if sc_type == "E":
                    lst_e.append(row)

                sc = {}
                list_text_mark.append(sc)

                sc["line"] = line
                sc["col"] = col
                sc["type"] = sc_type
                sc["params"] = list()

                n = False
                tx = ""
                for t in message:
                    if t == "'" and n is False:
                        n = True
                        continue

                    if t == "'" and n:
                        n = False
                        sc["params"].append(tx)
                        tx = ""
                        continue
                    if n:
                        tx += t

                tx = ""
                n = False
                for t in message:
                    if t == "(" and n is False:
                        n = True
                        continue

                    if t == ")" and n:
                        n = False
                        if tx.find('.') > -1:
                            tu = tx.split('.')
                            for tu1 in tu:
                                sc["params"].append(tu1)
                        else:
                            sc["params"].append(tx)
                        tx = ""
                        continue
                    if n:
                        tx += t

                message = message.replace("'", "")
                row["log"] = message
                row["codez"] = code
                row["pos"] = str(line) + ":" + str(col)
                row["col"] = col
                row["line"] = line
                row["type"] = sc_type
                c = c + 1

            lst_e.sort(key=operator.itemgetter('line'))
            lst_w.sort(key=operator.itemgetter('line'))
            for r in lst_e:
                self.table_log_py.rows.append(r)
            for r in lst_w:
                self.table_log_py.rows.append(r)

            if has_error is False:
                self.text_source_check = source
            else:
                self.text_source_check = ""

            for row in self.table_log_py.rows:

                lbType = Label()
                lbType.text = row["codez"]
                del row["codez"]
                if row["type"] == "W":
                    lbType.style = "color:orange"
                if row["type"] == "E":
                    lbType.style = "color:red"
                row.components["code"] = lbType
                row.aligns["log"] = [Alignment.AlignLeft, Alignment.AlignVCenter]
            self.check_tree()
            self.mark_workds(list_text_mark)
        except:
            traceback.print_exc()

    def mark_workds(self, list_text_mark):
        text = self.textEditor.text
        list_text_mark.sort(key=operator.itemgetter('line'))
        self.textEditor.list_text_mark.clear()
        lines = text.split("\n")
        for t in list_text_mark:
            if t["col"] == -1:
                continue
            if len(t["params"]) > 0:
                line = lines[t["line"] - 1]
                for p in t["params"]:
                    pos_s = line.find(p)
                    if pos_s >= 0:
                        w_end = pos_s + len(p)
                        tm = TextMark()
                        tm.start_position = TextUtil.get_position(text, t["line"], pos_s)
                        tm.end_position = TextUtil.get_position(text, t["line"], w_end)
                        if t["type"] == "W":
                            tm.color = "orange"
                        else:
                            tm.color = "red"
                        self.textEditor.list_text_mark.append(tm)
            else:
                pos_start = TextUtil.get_position(text, t["line"], t["col"])
                pos_end = pos_start + 1
                if text[pos_start:pos_end] == "\n":
                    continue

                tm = TextMark()
                tm.start_position = pos_start
                tm.end_position = pos_end
                if t["line"] == "W":
                    tm.color = "orange"
                else:
                    tm.color = "red"
                self.textEditor.list_text_mark.append(tm)

    def bt_organize_source(self):

        try:
            pos = self.textEditor.cursor_position.position
            source = self.textEditor.text
            list_ = FormatCode(source, style_config='pep8')
            if list_[1] is True:
                self.textEditor.text = list_[0]
                self.textEditor.cursor_position.position = pos
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            raise AlertException('E', 'kernel.lang.dev.000', str(exc_value))

    def bt_organize_source_xml(self):

        try:
            self.bt_check_source_xml()
            source = self.xml_editor.text
            dom = xml.dom.minidom.parseString(source)
            xmlz = dom.toprettyxml(indent='    ')
            dom_string = os.linesep.join(
                [s for s in xmlz.splitlines() if s.strip()])
            self.xml_editor.text = dom_string
        except:
            pass

    def active_source(self):
        self.check_source_xml(self.xml_editor)
        hasErr = True
        if self.text_source_check != self.textEditor.text:
            self.check_source(self.textEditor)
        if self.text_source_check == self.textEditor.text:
            hasErr = False

        if str(self.cb_viewxml.key_select) == 'True':
            if len(self.table_log_xml.rows) > 0:
                hasErr = True

        if (hasErr):
            msg: DMessage = DMessage("E", "kernel.lang.dev.018")
            msg.type = "E"
            self.alert_bar = msg
            return

        modreq = ModuleBox()
        modreq.module = self.module_active
        modreq.pkge = self.pkge_active
        modreq.source = self.encode_base64(self.textEditor.text)
        modreq.xml = self.encode_base64(self.xml_editor.text)
        modreq.desc = self.desc.text
        modreq.xml_view = self.srvr.xml_view

        request = SourceSave(self)
        request.set_return_func_status(self.return_active_source_save)
        request.set_module(modreq)
        request.save()

    def return_active_source_save(self, msg: DMessage, id_request: str):
        self.alert_bar = msg
        if msg.type == "E":
            return
        modreq = ModuleBox()
        modreq.module = self.module_active
        modreq.pkge = self.pkge_active
        modreq.source = self.encode_base64(self.textEditor.text)
        modreq.xml = self.encode_base64(self.xml_editor.text)
        modreq.desc = self.desc.text
        modreq.xml_view = self.srvr.xml_view

        request = SourceSave(self)
        request.set_return_func_status(self.return_active_source)
        request.set_module(modreq)
        request.active()

    def return_active_source(self, msg: DMessage):
        self.alert_bar = msg
        if msg.type == "E":
            return
        self.lb_status.text = "Active"
        self.bt_ative.image = "kernel.img.dev.active"

    def save_source(self):
        modreq = ModuleBox()
        modreq.module = self.module_active
        modreq.pkge = self.pkge_active
        modreq.source = self.encode_base64(self.textEditor.text)
        modreq.xml = self.encode_base64(self.xml_editor.text)
        modreq.desc = self.desc.text
        modreq.xml_view = self.srvr.xml_view

        request = SourceSave(self)
        request.set_return_func_status(self.return_save_request)
        request.set_module(modreq)
        request.save()

    def find_text(self):
        if self.get_focus() == self.textEditor:
            self.bt_find_text_py()

        if self.get_focus() == self.xml_editor:
            self.bt_find_text_xml()

    def check_delete_source(self):
        srvr = self.scAction.get_source(self.pkge.text, self.module.text)
        if srvr is None:
            msg = DMessage()
            msg.type = DMessage.ERROR
            msg.code = "kernel.lang.dev.005"
            msg.element1 = self.module.text
            msg.element2 = self.pkge.text
            self.alert_bar = msg
            return

        action1 = gettext("kernel.lang.dev.delete")
        action2 = gettext("kernel.lang.dev.cancel")
        module = '%s.%s' % (self.pkge.text, self.module.text)
        msg = gettext("kernel.lang.dev.061", module)
        dia = MessageDialog(self)
        dia.set_message(msg, action1, self.delete_source, action2)

    def delete_source(self):

        modreq = ModuleBox()
        modreq.module = self.module.text
        modreq.pkge = self.pkge.text
        modreq.source = self.encode_base64(self.textEditor.text)
        modreq.xml = self.encode_base64(self.xml_editor.text)
        modreq.desc = self.desc.text
        modreq.xml_view = self.srvr.xml_view

        request = SourceSave(self)
        request.set_return_func_status(self.return_active_source_delete)
        request.set_module(modreq)
        request.delete()

    def return_active_source_delete(self, msg: DMessage, id_request: str):
        self.alert_bar = msg
        if msg.type == "E":
            return

        self.go_to_class('kernel.editor.source_editor', 'ViewEditor')

    def finder(self):
        if self.get_focus() == self.textEditor:
            finder: FinderDialog = self.R.get_obj("finder_text_editor")
            finder.show()
        if self.get_focus() == self.xml_editor:
            finder: FinderDialog = self.R.get_obj("finder_xml_editor")
            finder.show()

    def return_save_request(self, msg: DMessage, id_request: str):
        if msg.type == "S":
            self.lb_status.text = "Inactive"
            self.bt_ative.image = "kernel.img.dev.inactive"
            self.set_value_temp()
            self.srvr = self.scAction.get_source(self.pkge_active,
                                                 self.module_active)
            self.lb_version.text = self.srvr.version
        self.alert_bar = msg

    def back_toolbar(self):

        self.set_focus(self.pkge)

    def check_debug(self):

        source = self.textEditor.text
        text = source.split("\n")
        rem = list()
        for line in self.textEditor.debug_lines:
            script = text[int(line) - 1]
            if script == '\r':
                rem.append(line)
            if script == '':
                rem.append(list)

        for u in rem:
            try:
                self.textEditor.debug_lines.remove(u)
            except:
                pass

        filename = ModuleUtil.get_module_to_file(self.pkge_active,
                                                 self.module_active)

        from kernel_profile import SY_BASE_DIR
        # filename = filename.replace("\\", "/")
        # filename = filename.replace(SY_BASE_DIR, ".")

        tr = threading.current_thread()

        rem = list()
        list_debug = RouteWorkProcess.get_all_debug(tr.rp.session_login)

        for conf_debug in list_debug:
            pkge, module = ModuleUtil.get_file_to_module(conf_debug["file"])
            if pkge == self.pkge_active and module == self.module_active:
                rem.append(conf_debug)

        for u in rem:
            RouteWorkProcess.remove_debug(u["file"], u["line"], tr.rp.session_login)
        for line in self.textEditor.debug_lines:
            RouteWorkProcess.add_debug(self.sy.user.user, filename, line, self.sy.user.user, tr.rp.session_login)
        ltemp = list(
            dict.fromkeys(self.textEditor.debug_lines))
        self.textEditor.debug_lines.clear()
        self.textEditor.debug_lines.extend(ltemp)

    def check_word(self, line, column, obj):
        # import fast  # pylint: disable=E0611,E0401
        # fast.sys_removetrace(self.sy.id_wp)  # pylint: disable=E0401

        self.textEditor.auto_complete = list()

        try:

            script = jedi.Script(code=self.textEditor.text, line=line + 1, column=column)

            # usages = script.usages()
            sign = script.goto(line=line + 1, column=column)
            if len(sign) > 0:
                obj_data = sign[0]
                pkge1, module1 = ModuleUtil.get_file_to_module(obj_data.module_path)
                self.to_module = None
                self.to_pkge = None
                self.to_line = None
                self.to_column = None
                if obj_data.type == "statement":
                    if pkge1 is None and module1 is None:
                        pos = TextUtil.get_position(self.textEditor.text,
                                                    obj_data.line,
                                                    obj_data.column)
                        if (obj_data.line - 1) != self.textEditor.cursor_position.line:
                            self.append_history("line", pos,
                                                self.textEditor.editable)
                        self.textEditor.cursor_position.position = pos
                    elif pkge1 != self.pkge_active or module1 != self.module_active:
                        self.to_module = module1
                        self.to_pkge = pkge1
                        self.to_line = obj_data.line
                        self.to_column = obj_data.column

                if obj_data.type == "class":
                    goto = script.goto(line=line + 1, column=column)
                    if len(goto) > 0:
                        go = goto[0]
                        pkge1, module1 = ModuleUtil.get_file_to_module(go.module_path)
                        if pkge1 is None and module1 is None:
                            pos = TextUtil.get_position(
                                self.textEditor.text, obj_data.line,
                                obj_data.column)
                            if (obj_data.line -
                                1) != self.textEditor.cursor_position.line:
                                self.append_history("line", pos,
                                                    self.textEditor.editable)
                            self.textEditor.cursor_position.position = pos
                        elif pkge1 != self.pkge_active or module1 != self.module_active:
                            path_mod = ModuleUtil.get_module_from_class(
                                obj_data.full_name)
                            self.to_module = ModuleUtil.get_module(path_mod)
                            self.to_pkge = ModuleUtil.get_pkge(path_mod)
                            self.to_line = obj_data.line
                            self.to_column = obj_data.column

                if obj_data.type == "function":
                    goto = script.goto(line=line + 1, column=column)
                    if len(goto) > 0:
                        go = goto[0]
                        if go.module_path is None:
                            pkge1, module1 = ModuleUtil.get_file_to_module(obj_data.module_path)
                        else:
                            pkge1, module1 = ModuleUtil.get_file_to_module(go.module_path)

                        if pkge1 is None and module1 is None:
                            pos = TextUtil.get_position(
                                self.textEditor.text, obj_data.line,
                                obj_data.column)
                            if (obj_data.line -
                                1) != self.textEditor.cursor_position.line:
                                self.append_history("line", pos,
                                                    self.textEditor.editable)
                            self.textEditor.cursor_position.position = pos
                        elif pkge1 != self.pkge_active or module1 != self.module_active:
                            self.to_pkge, self.to_module = pkge1, module1

                            self.to_line = obj_data.line
                            self.to_column = obj_data.column
                if self.to_module is not None and self.to_pkge is not None:
                    if self.textEditor.editable is True:
                        if self.source_save != self.textEditor.text or self.xml_save != self.xml_editor.text:
                            msg1 = gettext("kernel.lang.dev.save")
                            msg2 = gettext("kernel.lang.dev.notsave")
                            msg3 = gettext("kernel.lang.dev.cancel")
                            msg = gettext("kernel.lang.dev.021")
                            dia = MessageDialog(self)
                            dia.set_message(msg, msg1, self.res_save, msg2,
                                            self.go_module_view, msg3,
                                            self.res_cancel)
                        else:
                            self.go_module_view()
                    else:
                        self.go_module_view()
        except AlertException:
            raise
        except:
            traceback.print_exc()

    def go_module_view(self):
        module = self.module_active
        pkge = self.pkge_active
        self.view_source_call(self.to_pkge, self.to_module)
        if self.alert_bar is not None:
            if self.alert_bar.type == DMessage.ERROR:
                self.module_active = module
                self.pkge_active = pkge
                return
        pos = TextUtil.get_position(self.textEditor.text, self.to_line,
                                    self.to_column)

        self.append_history("file", pos, False)
        self.textEditor.cursor_position.position = pos
        self.check_history_source()

    def xml_auto_complete(self):
        session = getsession()
        source = self.xml_editor.text
        i = self.xml_editor.cursor_position.position
        pos = i
        type = None
        word = ""
        has_scape = False
        while i > 0:
            p = source[i - 1:i]

            if p == "\n":
                break

            if p == "<":
                type = "xml"
                break
            elif p == "{":
                type = "lang"
                break
            elif p == " ":
                word = ""
                has_scape = True
            else:
                word = p + word
            i -= 1

        self.xml_editor.auto_complete = []
        tags = []

        if type == "xml":
            self.xml_editor.auto_complete, tags = self.list_auto_complete_xml()
        if type == "xml" and has_scape:
            if word in tags:
                import importlib
                mod_ = importlib.import_module("kernel.obj.component")
                if hasattr(mod_, word):
                    class_ = getattr(mod_, word)
                    if hasattr(class_, "_attributes"):
                        self.xml_editor.auto_complete.clear()
                        class_._attributes.sort()
                        for item in class_._attributes:
                            if item not in ["identify", "reload_panel", "__changed"]:
                                self.xml_editor.auto_complete.append(AutoCompleteDoc([item]))
                        return

        if type == "lang":
            lang: str = source[i:pos]
            lang1 = lang.split(".")
            if len(lang1) == 0:
                return
            has_last = False
            if lang1[len(lang1) - 1] == "":
                has_last = True
                del lang1[len(lang1) - 1]

            list_auto_complete = {}

            pk = str(".".join(str(x) for x in lang1))
            q_pkge = session.query(Pkge).filter(
                Pkge.pkge.ilike(pk + "%")).all()
            for mod in q_pkge:
                th = AutoCompleteDoc()
                tx = gettext("kernel.lang.dev.045", mod.pkge, mod.name)
                th.row_values = [mod.pkge, "pkge: %s" % (mod.name)]
                th.text_help = tx
                list_auto_complete[mod.pkge] = th

            lst_check = []
            if len(lang1) > 1:
                l = len(lang1) - 1
                pk = str(".".join(str(x) for x in lang1[:l]))
                b = str(lang1[l]) + "%"
                if has_last:
                    b = str(lang1[l])
                q_class = session.query(Lang02).filter(
                    Lang02.pkge == pk,
                    Lang02.lang_class.ilike(b)).all()
                lst_check.extend(q_class)
                if len(q_class) == 0:
                    l = len(lang1)
                    pk = str(".".join(str(x) for x in lang1[:l]))
                    q_class = session.query(Lang02).filter(
                        Lang02.pkge == pk).all()
                    lst_check.extend(q_class)
                    if len(q_class) == 0 and len(lang1) > 2:
                        b = lang1[l - 2]
                        c = str(lang1[l - 1]) + "%"
                        pk = str(".".join(str(x) for x in lang1[:l - 2]))
                        q_class = session.query(Lang03).filter(
                            Lang03.pkge == pk,
                            Lang03.lang_class == b,
                            Lang03.keylang.ilike(c),
                            Lang03.lang == self.sy.language).all()
                        lst_check.extend(q_class)

                else:
                    b = lang1[l - 1]
                    c = lang1[l]

                    q_class = session.query(Lang03).filter(
                        Lang03.pkge == pk,
                        Lang03.lang_class == b,
                        Lang03.keylang == c,
                        Lang03.lang == self.sy.language).all()
                    lst_check.extend(q_class)
                    if len(q_class) == 0:
                        q_class = session.query(Lang03).filter(
                            Lang03.pkge == pk,
                            Lang03.lang_class == c,
                            Lang03.lang == self.sy.language).all()
                        lst_check.extend(q_class)
                        if len(q_class) == 0:
                            c = str(lang1[l]) + "%"
                            q_class = session.query(Lang03).filter(
                                Lang03.pkge == pk,
                                Lang03.lang_class == b,
                                Lang03.keylang.ilike(c),
                                Lang03.lang == self.sy.language).all()
                            lst_check.extend(q_class)

            for mod in lst_check:
                if isinstance(mod, Lang03):
                    th = AutoCompleteDoc()
                    tx = gettext("kernel.lang.dev.046", mod.pkge,
                                 mod.lang_class, mod.keylang,
                                 mod.text)
                    name = mod.pkge + "." + mod.lang_class + "." + mod.keylang
                    text = gettext(name)
                    if len(text) > 30:
                        text = text[:30]
                    th.row_values = [name, text]
                    th.text_help = tx
                    list_auto_complete[name] = th
                if isinstance(mod, Lang02):
                    th = AutoCompleteDoc()
                    name = mod.pkge + "." + mod.lang_class
                    th.row_values = [name, "class: %s" % (mod.desc)]
                    list_auto_complete[name] = th

            l = sorted(list_auto_complete)
            for key in l:
                self.xml_editor.auto_complete.append(list_auto_complete[key])

    def tip_mouse_select(self, position):
        source = self.xml_editor.text
        i = position
        pos = i
        type = None
        while i > 0:
            p = source[i - 1:i]
            if p == "\n":
                break
            if p == "<":
                type = "xml"
                break
            if p == "{":
                type = "lang"
                break
            i -= 1

        if type == "lang":
            while pos < len(source):
                p = source[pos - 1:pos]
                if p == "\n":
                    break
                if p == "<":
                    break
                if p == ">":
                    break
                if p == "}":
                    break
                pos += 1
            lang = source[i:pos - 1]
            self.xml_editor.mouse_tip_text = gettext(lang)

    def list_auto_complete_xml(self):
        lst = []
        lst.append("GridLayout")
        lst.append("View")
        lst.append("Scroller")
        lst.append("TabItem")
        lst.append("Tab")
        lst.append("HBoxLayout")
        lst.append("VBoxLayout")
        lst.append("FormLayout")
        lst.append("FormLayoutItem")
        lst.append("Label")
        lst.append("RadioButton")
        lst.append("DateTimeField")
        lst.append("DialogPanel")
        lst.append("TextField")
        lst.append("StatusField")
        lst.append("TextArea")
        lst.append("ComboBox")
        lst.append("ComboBoxItem")
        lst.append("TextEditorSource")
        lst.append("Table")
        lst.append("Column")
        lst.append("Columns")
        lst.append("Tree")
        lst.append("Button")
        lst.append("CheckBox")
        lst.append("Image")
        lst.append("SplitPane")
        lst.append("ToolBar")

        lst.sort()
        l = []
        for u in lst:
            l.append(AutoCompleteDoc([u]))
        return l, lst

    def py_auto_complete(self):
        # import fast  # pylint: disable=E0611,E0401
        # fast.sys_removetrace(self.sy.id_wp)  # pylint: disable=E0401
        source = self.textEditor.text
        self.textEditor.auto_complete = list()

        try:
            ln = self.textEditor.cursor_position.line
            cl = self.textEditor.cursor_position.column
            script = jedi.Script(code=source)

            completions = script.complete(line=ln,
                                          column=cl)
            sorted(completions, key=attrgetter('type', 'complete'))

            for comp in completions:
                help = AutoCompleteDoc()
                help.row_values = [comp.name, comp.type]
                self.textEditor.auto_complete.append(help)

                # if not str(comp.module_name).startswith("tempxy_")   :
                #     try:
                #         help.text_help = comp.docstring()
                #
                #     except:
                #         pass


        except:
            traceback.print_exc()

    def _next_code(self):
        self.view_source_call(self._temp_source["pkge"], self._temp_source["module"])
        self.textEditor.editable = self._temp_source["editable"]
        self.xml_editor.editable = self._temp_source["editable"]
        self.check_history_source()

    def _back_code(self):
        if self.source_index > 0:
            temp = self.source_history[self.source_index]
            source = self.source_history[self.source_index - 1]
            self.textEditor.cursor_position.position = source["position"]
            if temp["type"] == "file":
                if source["editable"]:
                    self.edit_source_call(source["pkge"], source["module"])
                    self.check_tree()
                else:
                    self.view_source_call(source["pkge"], source["module"])
                    self.check_tree()

        self.source_index -= 1
        self.check_history_source()

    def action_back_source(self):
        try:
            if len(self.source_history) > self.source_index:
                temp = self.source_history[self.source_index]
                back_button: Button = self.R.get_obj("bt_back_source")

                if temp["type"] == "file":
                    if (self.source_save != self.textEditor.text or self.xml_save != self.xml_editor.text) \
                            and back_button.enabled:
                        msg1 = gettext("kernel.lang.dev.save")
                        msg2 = gettext("kernel.lang.dev.notsave")
                        msg3 = gettext("kernel.lang.dev.cancel")
                        msg = gettext("kernel.lang.dev.021")
                        dia = MessageDialog(self)
                        dia.set_message(msg, msg1, self.res_save, msg2,
                                        self._back_code, msg3,
                                        self.res_cancel)
                        return
            self._back_code()
        except:
            pass

    def action_next_source(self):
        if len(self.source_history) > (self.source_index + 1):
            source = self.source_history[self.source_index + 1]
            next_button: Button = self.R.get_obj("bt_next_source")
            if source["type"] == "file":
                if (self.source_save != self.textEditor.text or self.xml_save != self.xml_editor.text) \
                        and next_button.enabled:
                    msg1 = gettext("kernel.lang.dev.save")
                    msg2 = gettext("kernel.lang.dev.notsave")
                    msg3 = gettext("kernel.lang.dev.cancel")
                    msg = gettext("kernel.lang.dev.021")
                    dia = MessageDialog(self)
                    dia.set_message(msg, msg1, self.res_save, msg2,
                                    self._next_code, msg3,
                                    self.res_cancel)
                    self._temp_source = source
                else:
                    self._temp_source = source
                    self._next_code()

            if source["type"] == "line":
                self.textEditor.cursor_position.position = source[
                    "position"]
                self.textEditor.editable = source["editable"]
                self.xml_editor.editable = source["editable"]

            self.source_index += 1
            self.check_history_source()

    def check_history_source(self):
        back_button: Button = self.R.get_obj("bt_back_source")
        next_button: Button = self.R.get_obj("bt_next_source")
        if back_button is None:
            return
        if self.source_index <= 0:
            back_button.enabled = False
            self.R.get_obj("menu_back1").enabled = False
        else:
            back_button.enabled = True
            self.R.get_obj("menu_back1").enabled = True

        if len(self.source_history) == 0:
            next_button.enabled = False
            self.R.get_obj("menu_next1").enabled = False
        else:
            if (self.source_index + 1) < len(self.source_history):
                next_button.enabled = True
                self.R.get_obj("menu_next1").enabled = True
            else:
                next_button.enabled = False
                self.R.get_obj("menu_next1").enabled = False

    def _check_history_buttton(self):
        self.check_history_source()
        super()._check_history_buttton()

    def prop_source(self):

        self.R.get_obj('d_desc').editable = self.textEditor.editable
        self.R.get_obj('d_desc').text = self.srvr.desc
        self.R.get_obj('d_cb_viewxml').editable = self.textEditor.editable
        self.R.get_obj('d_cb_viewxml').key_select = str(self.srvr.xml_view)
        self.R.get_obj('d_bt_save_prop').editable = not self.textEditor.editable
        self.dialog_detail.show()

    def save_properties(self):
        self.srvr.desc = self.R.get_obj('d_desc').text
        self.srvr.xml_view = eval(self.R.get_obj('d_cb_viewxml').key_select)
        self.dialog_detail.close()
        self.refresh()

    def cancel_properties(self):
        self.dialog_detail.close()

    def refresh(self):
        if self.srvr is not None:
            if self.source_index >= 0 and len(self.source_history) > self.source_index:
                self.source_history[self.source_index]["position"] = self.textEditor.cursor_position.position
            tab: Tab = self.R.get_obj("tab")
            xmlv = self.R.get_obj("tab_item_xml")
            prev = self.R.get_obj("tab_item_xml_preview")
            if self.srvr.xml_view is True:
                if xmlv not in tab:
                    tab.append(xmlv)
                if prev not in tab:
                    tab.append(prev)
            else:
                if xmlv in tab:
                    tab.remove(xmlv)
                if prev in tab:
                    tab.remove(prev)

        self.check_tree()
        if self.sizes_wight != self.splitSource.sizes or \
                self.sizes_height != self.splitLog.sizes:

            session = getsession()
            try:

                var03 = Var03()
                var03.varid = 'scspw1'
                var03.user = str(str(self.sy.user))
                var03.value = str(self.splitSource.sizes[0])
                session.merge(var03)

                var03 = Var03()
                var03.varid = 'scspw2'
                var03.user = str(str(self.sy.user))
                var03.value = str(self.splitSource.sizes[1])
                session.merge(var03)
                session.commit()

                var03 = Var03()
                var03.varid = 'scsph1'
                var03.user = str(str(self.sy.user))
                var03.value = str(self.splitLog.sizes[0])
                session.merge(var03)

                var03 = Var03()
                var03.varid = 'scsph2'
                var03.user = str(str(self.sy.user))
                var03.value = str(self.splitLog.sizes[1])
                session.merge(var03)
                session.commit()

                self.sizes_wight = self.splitSource.sizes
                self.sizes_height = self.splitLog.sizes

            except:
                traceback.print_exc()
