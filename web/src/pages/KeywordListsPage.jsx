import { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import {
  createKeywordListApi,
  listKeywordListsApi,
  addKeywordsToListApi,
  deleteKeywordListApi,
  exportKeywordListApi,
} from "../lib/api";
import { selectSelectedProject } from "../features/dashboard/dashboardSelectors";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Alert from "../components/ui/Alert";

export default function KeywordListsPage() {
  const selectedProject = useSelector(selectSelectedProject);

  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newListName, setNewListName] = useState("");
  const [activeList, setActiveList] = useState(null);
  const [newKeywords, setNewKeywords] = useState("");
  const [error, setError] = useState("");

  const loadLists = async () => {
    setLoading(true);
    try {
      const result = await listKeywordListsApi();
      setLists(result.data?.lists || []);
    } catch (err) {
      setError(err?.message || "Failed to load lists");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLists();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newListName.trim()) return;

    try {
      await createKeywordListApi(newListName);
      setNewListName("");
      await loadLists();
    } catch (err) {
      setError(err?.message || "Failed to create list");
    }
  };

  const handleAddKeywords = async (e) => {
    e.preventDefault();
    if (!newKeywords.trim() || !activeList) return;

    try {
      const keywords = newKeywords.split("\n").map((k) => k.trim()).filter(Boolean);
      await addKeywordsToListApi(activeList.id, keywords);
      setNewKeywords("");
      await loadLists();
      setActiveList(lists.find((l) => l.id === activeList.id) || null);
    } catch (err) {
      setError(err?.message || "Failed to add keywords");
    }
  };

  const handleDelete = async (listId) => {
    if (!confirm("Delete this list?")) return;
    try {
      await deleteKeywordListApi(listId);
      if (activeList?.id === listId) setActiveList(null);
      await loadLists();
    } catch (err) {
      setError(err?.message || "Failed to delete list");
    }
  };

  const handleExport = async (listId) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL || ''}/api/keyword-lists/${listId}/export`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("accessToken") || ""}` },
      });
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `keyword-list-${listId}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.message || "Failed to export list");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Keyword Lists</h1>
          <p className="text-slate-600">Save and organize keywords for later use</p>
        </div>

        {error && <Alert variant="error" message={error} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Lists sidebar */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Your Lists</h2>
            <form onSubmit={handleCreate} className="flex gap-2 mb-4">
              <Input
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                placeholder="New list name"
                className="flex-1"
              />
              <Button type="submit" disabled={!newListName.trim()}>Create</Button>
            </form>
            <div className="space-y-2">
              {lists.map((list) => (
                <div
                  key={list.id}
                  onClick={() => setActiveList(list)}
                  className={`p-3 rounded-lg border cursor-pointer transition ${
                    activeList?.id === list.id ? "border-blue-500 bg-blue-50" : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-slate-900">{list.name}</p>
                      <p className="text-xs text-slate-500">{list.items?.length || 0} keywords</p>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={(e) => { e.stopPropagation(); handleExport(list.id); }} className="text-xs text-blue-600 hover:text-blue-700">Export</button>
                      <button onClick={(e) => { e.stopPropagation(); handleDelete(list.id); }} className="text-xs text-red-600 hover:text-red-700">Delete</button>
                    </div>
                  </div>
                </div>
              ))}
              {lists.length === 0 && <p className="text-sm text-slate-500">No lists yet</p>}
            </div>
          </div>

          {/* Active list details */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            {activeList ? (
              <>
                <h2 className="text-lg font-semibold text-slate-900 mb-4">{activeList.name}</h2>
                <form onSubmit={handleAddKeywords} className="space-y-4">
                  <label className="block text-sm font-medium text-slate-700 mb-2">Add keywords (one per line)</label>
                  <textarea
                    value={newKeywords}
                    onChange={(e) => setNewKeywords(e.target.value)}
                    placeholder="keyword 1\nkeyword 2\nkeyword 3"
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={5}
                  />
                  <Button type="submit" disabled={!newKeywords.trim()}>Add Keywords</Button>
                </form>

                {activeList.items?.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-sm font-medium text-slate-700 mb-2">Keywords</h3>
                    <div className="max-h-[320px] overflow-y-auto">
                      <div className="flex flex-wrap gap-2">
                        {activeList.items.map((item) => (
                          <span key={item.id} className="px-3 py-1 bg-slate-100 border border-slate-200 rounded-full text-sm text-slate-700">
                            {item.keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-slate-500">Select a list to view details</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
