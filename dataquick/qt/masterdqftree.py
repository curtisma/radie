"""
define a QAbstractItemModel for a an Ordered Dict of an OrderedDict of DataQuickFrames, and also a
TreeView of the Items
"""

from PyQt5 import QtCore, QtWidgets

from .indexabledict import IndexableDict
from ..structures import DataQuickFrame
from . import dataframeview


class DQStructureTree(IndexableDict):
    """The main DataQuickFrame tree Construct

    This Class is the Root of the Tree of DataQuickFrames presented in the GUI viewer.  Essentially, it is an Ordered
    Dict whose keys are the DataQuickFrame classes, and whose values are the record of the available instances of those
    classes

    """
    def __init__(self):
        super(DQStructureTree, self).__init__()
        self.uuid = {}  # a place to track down DataFrames by uuid

    def __setitem__(self, key, value):
        if not issubclass(key, DataQuickFrame):
            raise TypeError("key must be a subclass of DataQuickFrame")
        if not isinstance(value, DQStructureNode):
            raise TypeError("DQFStructureTree items must be of type DQStructureNode")
        super(DQStructureTree, self).__setitem__(key, value)

    def addDataFrame(self, df):
        """the main api for adding in new DataFrames

        Parameters
        ----------
        df : DataQuickFrame

        Returns
        -------
        ref : DQFReference

        """
        uuid = df.get_uuid()
        if uuid in self.uuid.keys():
            raise ValueError("df already exists")
        insert_row = -1

        cls = df.__class__
        node = self.get(cls, None)
        if node is None:
            node = self[cls] = DQStructureNode(cls, self)
            insert_row = len(self)
        ref = node[uuid] = DQFReference(df, node)
        self.uuid[uuid] = ref

        return ref, node, insert_row


class DQStructureNode(IndexableDict):
    """A foldable node on the TreeView, one for each class of DataQuickFrame

    A dict whose keys are a uuid string generated by the DataQuickFrame instance, and the values are a reference to
    the DataQuickFrame of the class specified by the cls attribute

    Attributes
    ----------
    tree : DQStructureTree
        A reference to the parent tree
    cls : typing.Type(DataQuickFrame)
        The subclass of DataQuickFrame that all members of this node belong to
    """
    def __init__(self, cls, tree):
        self.cls = cls  # type: DataQuickFrame
        self.tree = tree  # type: DQStructureTree
        super(DQStructureNode, self).__init__()

    def parent(self):
        return self.tree

    def row(self):
        return self.tree.getKeyRow(self.cls)

    def pop(self, key):
        reference = super(DQStructureNode, self).pop(key)  # type: DQFReference
        reference.dqfDeleted.emit(reference)

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("keys must be a uuid string")
        elif not isinstance(value, DQFReference):
            raise TypeError("value must be of type {:}".format(DQFReference.__name__))

        super(DQStructureNode, self).__setitem__(key, value)


class DQFReference(QtCore.QObject):
    """A QObject which serves as a reference to a DataQuickFrame instance, and can emit Qt Signals when needed

    Attributes
    ----------
    df : DataQuickFrame
        The instance of a DataQuickFrame that this reference refers to
    node : DQStructureNode
        a reference to the parent node of this reference
    row : int
        the location of this item in the node
    """
    dataChanged = QtCore.pyqtSignal()
    dqfDeleted = QtCore.pyqtSignal(object)

    def __init__(self, df: DataQuickFrame, node: DQStructureNode):
        if not isinstance(df, DataQuickFrame):
            raise TypeError("df must be a DataQuickFrame")
        self._df = df
        self.node = node
        super(DQFReference, self).__init__()

    @property
    def df(self):
        return self._df

    def parent(self):
        return self.node

    def row(self):
        return self.node.getValueRow(self)

    @staticmethod
    def rowCount():
        return 0


class DQFTreeModel(QtCore.QAbstractItemModel):
    headers = ["Name", "uuid"]

    def __init__(self, root, parent=None):
        """
        Parameters
        ----------
        root : DQStructureTree
        parent : QtWidgets.QWidget
        """
        super(DQFTreeModel, self).__init__(parent)
        self.root = root
        for i, header in enumerate(self.headers):
            self.setHeaderData(i, QtCore.Qt.Horizontal, header)

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            pointer = self.root  # type: DQStructureTree
        else:
            pointer = parent.internalPointer()  # type: DQStructureNode
        child = pointer.getValue(row)

        index = self.createIndex(row, column, child)
        return index

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = ...):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.headers[section]
        else:
            return None

    def structureNodeIndex(self, cls, create=True):
        rootIndex = QtCore.QModelIndex()
        if cls not in self.root.keys():
            if not create:
                raise IndexError

            row = len(self.root)
            self.beginInsertRows(rootIndex, row, row)
            self.root[cls] = DQStructureNode(cls, self.root)
            self.endInsertRows()
        else:
            row = self.root.getKeyRow(cls)
        nodeIndex = self.index(row, 0, rootIndex)
        return nodeIndex

    def deleteDataFrame(self, index: QtCore.QModelIndex):
        df = index.internalPointer()
        if not isinstance(df, DQFReference):
            raise TypeError("index does not contain a DataFrame")
        row = index.row()
        self.beginRemoveRows(self.parent(index), row, row)
        node = df.parent()
        node.pop(df.df.uuid)
        self.endRemoveRows()

    def addDataFrame(self, df):
        """
        API for adding new dataframes after the model has been initiated

        Parameters
        ----------
        df : DataQuickFrame

        """
        cls = df.__class__
        nodeIndex = self.structureNodeIndex(cls, create=True)
        node = nodeIndex.internalPointer()
        row = len(node)
        self.beginInsertRows(nodeIndex, row, row)
        self.root.addDataFrame(df)
        self.endInsertRows()
        return nodeIndex

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not child.isValid():
            return QtCore.QModelIndex()

        item = child.internalPointer()
        if isinstance(item, DQFReference):
            node = item.parent()
            row = node.row()
            return self.createIndex(row, 0, node)
        else:  # item is DQStructureNode
            return QtCore.QModelIndex()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        if parent.isValid():
            pointer = parent.internalPointer()
            return pointer.rowCount()
        else:
            return self.root.rowCount()

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return 2  # 1: class_name or FamilyMember.name | 2: FamilyMember.age

    def hasChildren(self, parent: QtCore.QModelIndex = ...) -> bool:
        item = parent.internalPointer()
        if isinstance(item, DQFReference):
            return False
        else:
            return True

    def data(self, index: QtCore.QModelIndex, role: int = ...):
        if not index.isValid():
            return None
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            item = index.internalPointer()
            if isinstance(item, DQStructureNode):
                if index.column() == 0:
                    return item.cls.__name__
            elif isinstance(item, DQFReference):
                if index.column() == 0:
                    return item._df.metadata["name"]
                elif index.column() == 1:
                    return item._df.get_uuid()
                else:
                    return None
        else:  # Not display or Edit
            return None

    def setData(self, index: QtCore.QModelIndex, value, role: int = ...):
        item = index.internalPointer()
        col = index.column()
        if isinstance(item, DQFReference):
            if col == 0:
                item._df.metadata["name"] = str(value)
            else:
                return False
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QtCore.QModelIndex):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        item = index.internalPointer()
        if isinstance(item, DQFReference):
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | \
                   QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled
        elif isinstance(item, DQStructureNode):
            return QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable


class DQFTreeView(QtWidgets.QTreeView):
    def __init__(self, data=None, parent=None):
        super(DQFTreeView, self).__init__(parent)
        if not isinstance(data, DQStructureTree):
            self.data = DQStructureTree()
        else:
            self.data = data
        model = DQFTreeModel(self.data)
        self.setModel(model)
        rootIndex = QtCore.QModelIndex()
        for row in range(len(self.data)):
            self.setExpanded(model.index(row, 0, rootIndex), True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)
        self.setSelectionMode(self.ExtendedSelection)
        self.setDragDropMode(self.DragDrop)

    def getSelectedDataFrameIndices(self):
        selected_df_indices = list()
        for index in self.selectionModel().selectedRows(0):  # type: QtCore.QModelIndex
            pointer = index.internalPointer()
            if isinstance(pointer, DQFReference):
                selected_df_indices.append(index)
        return selected_df_indices

    def deleteSelectedDataFrames(self):
        for index in self.getSelectedDataFrameIndices():  # type: QtCore.QModelIndex
            self.model().deleteDataFrame(index)

    def viewSelectedDataFrame(self):
        row = self.selectionModel().selectedRows(0)[0]
        pointer = row.internalPointer()
        if isinstance(pointer, DQFReference):
            dataframeview.viewDataFrame(pointer.df)

    def copySelectedDataFrame(self):
        row = self.selectionModel().selectedRows(0)[0]
        pointer = row.internalPointer()
        if isinstance(pointer, DQFReference):
            pointer.df.to_clipboard(excel=True)

    def rightClicked(self, pos: QtCore.QPoint):
        menu = QtWidgets.QMenu()

        selected_rows = self.selectionModel().selectedRows(column=0)
        num_dataframes = len(selected_rows)

        if num_dataframes > 0:
            if num_dataframes == 1:
                deleteItem = QtWidgets.QAction("Delete DataFrame", menu)
                viewItem = QtWidgets.QAction("View DataFrame", menu)
                viewItem.triggered.connect(self.viewSelectedDataFrame)
                menu.addAction(viewItem)
                copyItem = QtWidgets.QAction("Copy DataFrame", menu)
                copyItem.triggered.connect(self.copySelectedDataFrame)
                menu.addAction(copyItem)
            else:
                deleteItem = QtWidgets.QAction("Delete DataFrames", menu)

            deleteItem.triggered.connect(self.deleteSelectedDataFrames)
            menu.addAction(deleteItem)

        menu.exec_(self.mapToGlobal(pos))  # QtWidgets.QAction

    def addDataFrame(self, df):
        model = self.model()  # type: DQFTreeModel
        nodeIndex = model.addDataFrame(df)
        self.setExpanded(nodeIndex, True)
        self.resizeColumnToContents(0)


def test():
    """function to test DQFTree from"""
    import sys
    app = QtWidgets.QApplication(sys.argv)
    from dataquick.plugins import examples
    vsm1 = examples.example_vsm()
    vsm2 = examples.example_vsm()
    pow1 = examples.example_powderdiffraction()
    pow2 = examples.example_powderdiffraction()

    data = DQStructureTree()
    for df in (vsm1, vsm2):
        data.addDataFrame(df)

    def _excepthook(e, v, t):
        sys.__excepthook__(e, v, t)

    sys.excepthook = _excepthook
    tree_view = DQFTreeView(data)
    tree_view.show()
    pow2.name = "Second XRD"
    for df in (pow1, pow2):
        tree_view.addDataFrame(df)
    sys.exit(app.exec_())
