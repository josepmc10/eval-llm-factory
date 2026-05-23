import os
import json
import socket
import webbrowser
import threading
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

from eval_factory.config import config
from eval_factory.serialization import RobustEncoder

# The highly premium Single Page Application (SPA) HTML template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>eval-factory Dashboard</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        outfit: ['Outfit', 'sans-serif'],
                        mono: ['Fira Code', 'monospace']
                    }
                }
            }
        }
    </script>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <!-- FontAwesome for Premium Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Alpine.js CDN -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <!-- SheetJS CDN for Excel Generation -->
    <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>

    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #090d16;
            color: #e2e8f0;
        }
        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: #0b0f19;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #334155;
        }
        .glass-card {
            background: rgba(19, 27, 46, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(31, 46, 77, 0.5);
        }
        .glow-accent {
            box-shadow: 0 0 25px rgba(59, 130, 246, 0.15);
        }
        .glow-green {
            box-shadow: 0 0 25px rgba(16, 185, 129, 0.1);
        }
    </style>
</head>
<body class="min-h-screen custom-scrollbar transition-colors duration-300" :class="darkMode ? 'bg-[#090d16] text-[#e2e8f0]' : 'bg-[#f8fafc] text-slate-900'" x-data="dashboard">
    <!-- App Wrapper -->
    <div class="flex flex-col h-screen overflow-hidden">
        
        <!-- Header -->
        <header :class="darkMode ? 'border-[#1f2e4d] bg-[#0b0f19]/90' : 'border-slate-200 bg-white/95 shadow-sm'"
                class="border-b px-8 py-4 flex items-center justify-between z-10 transition-colors duration-300">
            <div class="flex items-center space-x-3">
                <div class="bg-gradient-to-tr from-blue-600 to-indigo-500 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                    <i class="fa-solid fa-flask text-white text-xl"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold font-outfit bg-gradient-to-r from-blue-400 via-indigo-200 to-white bg-clip-text text-transparent">
                        eval-factory
                    </h1>
                    <p :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="text-xs transition-colors duration-300">Interactive Evaluation Suite</p>
                </div>
            </div>

            <!-- Navigation Tabs -->
            <div :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d]' : 'bg-slate-100 border-slate-200'"
                 class="flex space-x-1 p-1 rounded-xl border transition-colors duration-300">
                <button @click="activeTab = 'runs'" 
                        :class="activeTab === 'runs' ? 'bg-blue-600 text-white font-bold shadow-md shadow-blue-500/20' : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900')" 
                        class="px-5 py-2 text-sm rounded-lg flex items-center space-x-2 transition font-outfit">
                    <i class="fa-solid fa-flask-vial"></i>
                    <span>Evaluation Runs</span>
                </button>
                <button @click="activeTab = 'ground_truth'" 
                        :class="activeTab === 'ground_truth' ? 'bg-blue-600 text-white font-bold shadow-md shadow-blue-500/20' : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900')" 
                        class="px-5 py-2 text-sm rounded-lg flex items-center space-x-2 transition font-outfit">
                    <i class="fa-solid fa-file-excel"></i>
                    <span>Ground Truth Generator</span>
                </button>
            </div>
            
            <div class="flex items-center space-x-4">
                <!-- Theme Toggler (Dark/Light Switcher) -->
                <button @click="darkMode = !darkMode" 
                        :class="darkMode ? 'bg-[#131b2e] border-[#1f2e4d] text-amber-400 hover:text-amber-300' : 'bg-white border-slate-200 text-indigo-600 hover:text-indigo-700 shadow-sm'"
                        class="p-2.5 rounded-xl border transition-all duration-300 flex items-center justify-center cursor-pointer transform hover:scale-105 active:scale-95 animate-none"
                        title="Toggle Light/Dark Theme">
                    <template x-if="darkMode">
                        <i class="fa-solid fa-sun text-sm"></i>
                    </template>
                    <template x-if="!darkMode">
                        <i class="fa-solid fa-moon text-sm"></i>
                    </template>
                </button>

                <span class="text-sm font-semibold text-slate-500">Dataset File:</span>
                <div :class="darkMode ? 'bg-indigo-950/40 border-indigo-500/30 text-indigo-300' : 'bg-indigo-50 border-indigo-200 text-indigo-700'"
                     class="px-3.5 py-2 rounded-lg border font-mono text-sm flex items-center space-x-2 transition-all">
                    <i class="fa-solid fa-file-invoice-dollar"></i>
                    <span>{{DATASET_NAME}}.jsonl</span>
                </div>
                <a href="/api/download" download 
                   :class="darkMode ? 'text-slate-300 hover:text-white bg-[#131b2e] border-[#1f2e4d] hover:border-slate-500' : 'text-slate-700 hover:text-slate-900 bg-white border-slate-300 hover:border-slate-400 hover:bg-slate-50 shadow-sm'"
                   class="transition px-3.5 py-2 rounded-lg border text-sm font-semibold flex items-center space-x-1.5 font-outfit shadow-md cursor-pointer">
                    <i class="fa-solid fa-file-arrow-down text-blue-400"></i>
                    <span>Export JSONL</span>
                </a>
                <button @click="fetchRuns()" 
                        :class="darkMode ? 'text-slate-400 hover:text-white bg-[#131b2e] border-[#1f2e4d]' : 'text-slate-600 hover:text-slate-900 bg-white border-slate-300 hover:bg-slate-50'"
                        class="transition p-2 rounded-lg border">
                    <i class="fa-solid fa-rotate"></i>
                </button>
            </div>
        </header>

        <!-- KPI Metrics & Grid Dashboard -->
        <div class="flex-1 flex overflow-hidden">
            
            <!-- Main Content Area -->
            <div class="flex-1 flex flex-col overflow-hidden px-8 py-6 space-y-6">
                
                <!-- KPI Dashboard Counters -->
                <div class="grid grid-cols-4 gap-6">
                    <div :class="darkMode ? 'glass-card border-[#1f2e4d] bg-[#131b2e]/20' : 'bg-white border-slate-200 shadow-sm'"
                         class="rounded-2xl p-5 flex items-center space-x-4 border transition-all duration-300">
                        <div class="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-xl">
                            <i class="fa-solid fa-database"></i>
                        </div>
                        <div>
                            <p :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="text-[13px] uppercase font-semibold tracking-wider font-outfit">Captured Runs</p>
                            <h3 :class="darkMode ? 'text-white' : 'text-slate-950'" class="text-3xl font-bold font-outfit mt-0.5" x-text="totalRuns">0</h3>
                        </div>
                    </div>
                    
                    <div :class="darkMode ? 'glass-card border-[#1f2e4d] bg-[#131b2e]/20' : 'bg-white border-slate-200 shadow-sm'"
                         class="rounded-2xl p-5 flex items-center space-x-4 border transition-all duration-300">
                        <div class="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-xl">
                            <i class="fa-solid fa-clock"></i>
                        </div>
                        <div>
                            <p :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="text-[13px] uppercase font-semibold tracking-wider font-outfit">Avg Latency</p>
                            <h3 :class="darkMode ? 'text-white' : 'text-slate-950'" class="text-3xl font-bold font-outfit mt-0.5" x-text="avgDuration + 's'">0s</h3>
                        </div>
                    </div>
                    
                    <div :class="darkMode ? 'glass-card border-[#1f2e4d] bg-[#131b2e]/20' : 'bg-white border-slate-200 shadow-sm'"
                         class="rounded-2xl p-5 flex items-center space-x-4 border transition-all duration-300">
                        <div class="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 text-xl">
                            <i class="fa-solid fa-receipt"></i>
                        </div>
                        <div>
                            <p :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="text-[13px] uppercase font-semibold tracking-wider font-outfit">Estimated Cost</p>
                            <h3 :class="darkMode ? 'text-white' : 'text-slate-950'" class="text-3xl font-bold font-outfit mt-0.5" x-text="'$' + totalCost">$0.0000</h3>
                        </div>
                    </div>
                    
                    <div :class="darkMode ? 'glass-card border-[#1f2e4d] bg-[#131b2e]/20 glow-green' : 'bg-white border-slate-200 shadow-sm'"
                         class="rounded-2xl p-5 flex items-center space-x-4 border transition-all duration-300">
                        <div class="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-xl">
                            <i class="fa-solid fa-square-poll-vertical"></i>
                        </div>
                        <div>
                            <p :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="text-[13px] uppercase font-semibold tracking-wider font-outfit">Correctness Rate</p>
                            <h3 :class="darkMode ? 'text-white' : 'text-slate-950'" class="text-3xl font-bold font-outfit mt-0.5" x-text="accuracy">N/A</h3>
                        </div>
                    </div>
                </div>

                <!-- Main Layout splits List and Inspector -->
                <div x-show="activeTab === 'runs'" class="flex-1 flex overflow-hidden gap-6">
                    
                    <!-- LEFT COLUMN: Runs List -->
                    <div :class="darkMode ? 'glass-card border-[#1f2e4d]' : 'bg-white border-slate-200 shadow-sm'"
                         class="w-1/3 flex flex-col rounded-2xl overflow-hidden border transition-all duration-300">
                        <!-- Search and Filter -->
                        <div :class="darkMode ? 'border-[#1f2e4d] bg-[#0b0f19]/40' : 'border-slate-100 bg-slate-50/80'"
                             class="p-4 border-b space-y-3 transition-colors duration-300">
                            <div class="relative">
                                <i class="fa-solid fa-magnifying-glass absolute left-3 top-3 text-slate-400 text-sm"></i>
                                <input type="text" x-model="searchQuery" placeholder="Search inputs & outputs..." 
                                       :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-white' : 'bg-white border-slate-300 text-slate-900 focus:ring-1 focus:ring-blue-500'"
                                       class="w-full border rounded-xl pl-9 pr-4 py-2 text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500 transition">
                            </div>
                            
                            <!-- Filter Tabs -->
                            <div :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d]' : 'bg-slate-100 border-slate-200'"
                                 class="flex space-x-1 p-1 rounded-lg border transition-colors duration-300">
                                <button @click="statusFilter = 'all'" :class="statusFilter === 'all' ? (darkMode ? 'bg-[#1e293b] text-white' : 'bg-white text-slate-900 shadow-xs') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="flex-1 py-1.5 text-sm rounded font-medium transition">All</button>
                                <button @click="statusFilter = 'correct'" :class="statusFilter === 'correct' ? (darkMode ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="flex-1 py-1.5 text-sm rounded font-medium transition">Correct</button>
                                <button @click="statusFilter = 'incorrect'" :class="statusFilter === 'incorrect' ? (darkMode ? 'bg-rose-950/80 text-rose-400 border border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="flex-1 py-1.5 text-sm rounded font-medium transition">Incorrect</button>
                                <button @click="statusFilter = 'pending'" :class="statusFilter === 'pending' ? (darkMode ? 'bg-[#1e293b] text-white' : 'bg-white text-slate-900 shadow-xs') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="flex-1 py-1.5 text-sm rounded font-medium transition">Pending</button>
                            </div>
                        </div>

                        <!-- Scrollable Cards -->
                        <div :class="darkMode ? 'bg-[#0b0f19]/20' : 'bg-slate-50/20'"
                             class="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2 transition-colors duration-300">
                            <!-- Loading / Empty States -->
                            <template x-if="loading">
                                <div class="text-center py-12 text-slate-400 space-y-2">
                                    <i class="fa-solid fa-circle-notch fa-spin text-2xl text-blue-500"></i>
                                    <p class="text-xs">Loading dataset records...</p>
                                </div>
                            </template>
                            <template x-if="!loading && filteredRuns.length === 0">
                                <div class="text-center py-12 text-slate-500 space-y-2">
                                    <i class="fa-solid fa-inbox text-3xl"></i>
                                    <p class="text-xs">No matching runs found.</p>
                                </div>
                            </template>

                            <!-- Run Cards -->
                            <template x-for="run in filteredRuns" :key="run.run_id">
                                <div @click="selectRun(run)" 
                                     :class="selectedRun && selectedRun.run_id === run.run_id ? 
                                             (darkMode ? 'border-blue-500 bg-blue-950/20' : 'border-blue-500 bg-blue-50/50') : 
                                             (darkMode ? 'border-[#1f2e4d] hover:border-slate-600 bg-[#131b2e]/40' : 'border-slate-200 hover:border-slate-300 bg-white')"
                                     class="p-4 rounded-xl border transition cursor-pointer text-left relative flex flex-col space-y-2">
                                    
                                    <div class="flex justify-between items-start">
                                        <!-- Correctness Badge -->
                                        <template x-if="getRunStatus(run).type === 'correct'">
                                            <span class="px-2.5 py-0.5 text-xs font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                                                <i class="fa-solid fa-circle-check mr-1"></i> Correct
                                            </span>
                                        </template>
                                        <template x-if="getRunStatus(run).type === 'incorrect'">
                                            <span class="px-2.5 py-0.5 text-xs font-semibold rounded bg-rose-950 text-rose-400 border border-rose-500/30">
                                                <i class="fa-solid fa-circle-xmark mr-1"></i> <span x-text="getRunStatus(run).label"></span>
                                            </span>
                                        </template>
                                        <template x-if="getRunStatus(run).type === 'partial'">
                                            <span class="px-2.5 py-0.5 text-xs font-semibold rounded bg-amber-950/80 text-amber-400 border border-amber-500/30 font-medium">
                                                <i class="fa-solid fa-circle-notch mr-1"></i> <span x-text="getRunStatus(run).label"></span>
                                            </span>
                                        </template>
                                        <template x-if="getRunStatus(run).type === 'pending'">
                                            <span class="px-2.5 py-0.5 text-xs font-semibold rounded bg-[#1e293b] text-slate-300">
                                                <i class="fa-solid fa-circle-question mr-1"></i> Pending
                                            </span>
                                        </template>

                                        <!-- Timestamp -->
                                        <span class="text-xs text-slate-500" x-text="formatTime(run.timestamp)">Just now</span>
                                    </div>

                                    <!-- input preview -->
                                    <p :class="darkMode ? 'text-slate-200' : 'text-slate-700'" class="text-base font-medium line-clamp-2" x-text="getSidebarPreview(run)"></p>
                                    
                                    <!-- mini stats -->
                                    <div class="flex items-center space-x-3 text-xs text-slate-400 font-mono">
                                        <span><i class="fa-solid fa-hourglass-half mr-1 text-slate-500"></i> <span x-text="parseFloat(run.metadata?.duration_seconds || 0).toFixed(2) + 's'"></span></span>
                                        <template x-if="run.metadata?.tokens">
                                            <span><i class="fa-solid fa-coins mr-1 text-slate-500"></i> <span x-text="run.metadata.tokens.total_tokens + ' t'"></span></span>
                                        </template>
                                    </div>
                                </div>
                            </template>
                        </div>
                    </div>

                    <!-- RIGHT COLUMN: Run Inspector -->
                    <div :class="darkMode ? 'glass-card border-[#1f2e4d] bg-[#131b2e]/20' : 'bg-white border-slate-200 shadow-sm'"
                         class="w-2/3 flex flex-col rounded-2xl overflow-hidden border transition-all duration-300">
                        <template x-if="!selectedRun">
                            <div class="flex-1 flex flex-col items-center justify-center text-slate-500 space-y-3">
                                <i class="fa-solid fa-flask-vial text-5xl bg-gradient-to-tr from-blue-500/10 to-indigo-500/10 p-6 rounded-3xl border border-indigo-500/10"></i>
                                <p class="text-sm">Select a captured run from the list to inspect it.</p>
                            </div>
                        </template>
                        
                        <template x-if="selectedRun">
                            <div class="flex-grow flex flex-col overflow-hidden">
                                <!-- Inspector Header -->
                                <div :class="darkMode ? 'border-[#1f2e4d] bg-[#0b0f19]/40' : 'border-slate-100 bg-slate-50/80'"
                                     class="p-6 border-b flex items-center justify-between transition-colors duration-300">
                                    <div>
                                        <div class="flex items-center space-x-2">
                                            <h2 :class="darkMode ? 'text-white' : 'text-slate-900'" class="text-xl font-bold font-outfit">Run Inspector</h2>
                                            <span :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-slate-500' : 'bg-slate-100 border-slate-300 text-slate-600'"
                                                  class="text-sm font-mono px-2.5 py-0.5 rounded border transition-all" x-text="selectedRun?.run_id ? selectedRun.run_id.substring(0, 8) + '...' : ''"></span>
                                        </div>
                                        <p :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="text-sm mt-1.5 transition-colors" x-text="selectedRun ? 'Executed on: ' + new Date(selectedRun.timestamp).toLocaleString() : ''">Just now</p>
                                    </div>

                                    <!-- Top Right Mini Badges -->
                                    <div :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d]' : 'bg-slate-100 border-slate-200'"
                                         class="flex space-x-3 text-sm font-mono px-4.5 py-2.5 rounded-xl border transition-all">
                                        <div>
                                            <span class="text-slate-500">Latency:</span>
                                            <span class="text-blue-400 font-semibold" x-text="parseFloat(selectedRun?.metadata?.duration_seconds || 0).toFixed(3) + 's'"></span>
                                        </div>
                                        <div :class="darkMode ? 'border-slate-700' : 'border-slate-300'" class="border-l h-4 my-auto mx-2"></div>
                                        <template x-if="selectedRun?.metadata?.tokens">
                                            <div class="flex space-x-3">
                                                <div>
                                                    <span class="text-slate-500">Tokens:</span>
                                                    <span class="text-purple-400 font-semibold" x-text="selectedRun?.metadata?.tokens?.total_tokens || 0"></span>
                                                </div>
                                                <div :class="darkMode ? 'border-slate-700' : 'border-slate-300'" class="border-l h-4 my-auto mx-2"></div>
                                                <div>
                                                    <span class="text-slate-500">Cost:</span>
                                                    <span class="text-emerald-400 font-semibold" x-text="selectedRun?.metadata?.tokens?.total_cost ? '$' + selectedRun.metadata.tokens.total_cost.toFixed(4) : '$0.0000'"></span>
                                                </div>
                                            </div>
                                        </template>
                                    </div>
                                </div>

                                <!-- Inspector Scrollable Body -->
                                <div :class="darkMode ? 'bg-[#0b0f19]/10' : 'bg-slate-50/30'"
                                     class="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6 transition-colors duration-300">
                                    
                                    <!-- 1. System Prompt (collapsible) -->
                                    <template x-if="selectedRun?.metadata?.system_prompts && selectedRun.metadata.system_prompts.length > 0">
                                        <div x-data="{ open: false }" 
                                             :class="darkMode ? 'border-indigo-500/20 bg-indigo-950/20' : 'border-indigo-200 bg-indigo-50/40'"
                                             class="rounded-xl border p-4 space-y-2 transition-all">
                                            <button @click="open = !open" class="w-full flex items-center justify-between text-sm font-bold text-indigo-400 uppercase tracking-wider font-outfit focus:outline-none">
                                                <div class="flex items-center space-x-2">
                                                    <i class="fa-solid fa-robot animate-pulse"></i>
                                                    <span>System Prompt (<span x-text="selectedRun?.metadata?.system_prompts?.length || 0"></span> captured)</span>
                                                </div>
                                                <i class="fa-solid text-indigo-300 transition-transform duration-200" :class="open ? 'fa-chevron-up rotate-180' : 'fa-chevron-down'"></i>
                                            </button>
                                            <div x-show="open" x-transition 
                                                 :class="darkMode ? 'bg-[#090d16]/60 border-indigo-950/60 text-slate-300' : 'bg-white border-indigo-100 text-slate-700'"
                                                 class="mt-2 text-[17px] leading-relaxed font-mono whitespace-pre-wrap p-3.5 rounded-lg border" x-text="getSystemPromptsText()"></div>
                                        </div>
                                    </template>

                                    <!-- 2. Pair Cards Iterator -->
                                    <template x-for="(ev, index) in (selectedRun?.evaluation || [])" :key="index">
                                        <div x-data="{ showMetadata: false }" 
                                             :class="darkMode ? 'glass-card border-[#1f2e4d] bg-[#131b2e]/30 shadow-xl' : 'bg-white border-slate-200 shadow-md'"
                                             class="rounded-2xl p-6 border space-y-4 transition-all duration-300">
                                            
                                            <!-- Pair Header -->
                                            <div :class="darkMode ? 'border-[#1f2e4d]/80' : 'border-slate-200'"
                                                 class="flex items-center justify-between border-b pb-3 transition-colors">
                                                <div class="flex items-center space-x-2">
                                                    <span class="w-7 h-7 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-sm font-bold text-blue-400" x-text="index + 1"></span>
                                                    <h3 :class="darkMode ? 'text-white' : 'text-slate-900'" class="text-base font-bold font-outfit">Evaluation Pair #<span x-text="index + 1"></span></h3>
                                                </div>
                                                
                                                <!-- Mini Status for Pair -->
                                                <div>
                                                    <template x-if="ev.correct === true">
                                                        <span class="px-3 py-1 text-sm font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                                                            <i class="fa-solid fa-circle-check mr-1"></i> Correct
                                                        </span>
                                                    </template>
                                                    <template x-if="ev.correct === false">
                                                        <span class="px-3 py-1 text-sm font-semibold rounded bg-rose-950 text-rose-400 border border-rose-500/30">
                                                            <i class="fa-solid fa-circle-xmark mr-1"></i> Incorrect
                                                        </span>
                                                    </template>
                                                    <template x-if="ev.correct === null || ev.correct === undefined">
                                                        <span :class="darkMode ? 'bg-[#1e293b] text-slate-400 border-[#1f2e4d]' : 'bg-slate-100 text-slate-500 border-slate-300'"
                                                              class="px-3 py-1 text-sm font-semibold rounded border">
                                                            <i class="fa-solid fa-circle-question mr-1"></i> Pending Review
                                                        </span>
                                                    </template>
                                                </div>
                                            </div>

                                            <!-- Clean Input Prompt Preview -->
                                            <div class="space-y-1.5 text-left">
                                                <span class="text-sm font-bold text-slate-400 uppercase tracking-wider">Input Prompt</span>
                                                <div :class="darkMode ? 'bg-[#0b0f19]/60 border-[#1f2e4d]/60 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'"
                                                     class="rounded-xl p-3.5 text-[17px] leading-relaxed font-medium whitespace-pre-wrap select-all border"
                                                     x-text="getCleanText(getPairInput(selectedRun, index))">
                                                </div>
                                            </div>

                                            <!-- Clean Model Response (Big Content Box) -->
                                            <div class="space-y-1.5 text-left">
                                                <span class="text-sm font-bold text-blue-400 uppercase tracking-wider font-outfit flex items-center space-x-1.5">
                                                    <i class="fa-solid fa-magic-wand-sparkles"></i>
                                                    <span>Model Response</span>
                                                </span>
                                                <div :class="darkMode ? 'from-[#1e293b]/40 to-[#0f172a]/70 border-blue-500/25 text-slate-100' : 'from-slate-50 to-slate-100 border-blue-200 text-slate-800'"
                                                     class="bg-gradient-to-br border text-xl font-outfit font-medium leading-relaxed p-5 rounded-2xl shadow-inner whitespace-pre-wrap select-all transition-all duration-300"
                                                     x-text="getCleanText(isBatchRun(selectedRun) ? selectedRun.outputs[index] : selectedRun.outputs)">
                                                </div>
                                            </div>

                                            <!-- Evaluator Playground (Always visible under big content) -->
                                            <div :class="darkMode ? 'border-[#1f2e4d]/40' : 'border-slate-200'"
                                                 class="grid grid-cols-3 gap-4 items-end pt-3 border-t">
                                                <div class="col-span-2 space-y-1.5 text-left">
                                                    <label class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Expected Ground Truth Response (Optional)</label>
                                                    
                                                    <!-- Case A: Plain Text Ground Truth -->
                                                    <template x-if="!getOutputStructuredFields(isBatchRun(selectedRun) ? selectedRun.outputs[index] : selectedRun.outputs)">
                                                        <input type="text" x-model="ev.ground_truth" placeholder="Define expected output..." 
                                                               :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400 focus:ring-1 focus:ring-blue-500'"
                                                               class="w-full border rounded-xl px-3.5 py-2.5 text-base focus:outline-none focus:border-blue-500 transition">
                                                    </template>
                                                    
                                                    <!-- Case B: Structured Ground Truth (1 field for each output field) -->
                                                    <template x-if="getOutputStructuredFields(isBatchRun(selectedRun) ? selectedRun.outputs[index] : selectedRun.outputs)">
                                                        <div :class="darkMode ? 'bg-[#090d16]/30 border-[#1f2e4d]/40' : 'bg-slate-50 border-slate-200'"
                                                             class="grid grid-cols-2 gap-3 p-3 rounded-xl border">
                                                            <template x-for="field in getOutputStructuredFields(isBatchRun(selectedRun) ? selectedRun.outputs[index] : selectedRun.outputs)" :key="field">
                                                                <div class="space-y-1">
                                                                    <span :class="darkMode ? 'text-slate-400' : 'text-slate-600'" class="text-sm font-semibold uppercase tracking-wider font-mono" x-text="field"></span>
                                                                    <input type="text" x-model="ev.ground_truth[field]" :placeholder="'Enter ' + field + '...'"
                                                                           :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400 focus:ring-1 focus:ring-blue-500'"
                                                                           class="w-full border rounded-lg px-3 py-2 text-base focus:outline-none focus:border-blue-500 transition">
                                                                </div>
                                                            </template>
                                                        </div>
                                                    </template>
                                                </div>

                                                <div class="space-y-1.5 flex flex-col justify-end text-left">
                                                    <label class="text-sm font-semibold text-slate-400 uppercase tracking-wider">Correctness</label>
                                                    <div class="flex space-x-1">
                                                        <button @click="ev.correct = true" 
                                                                :class="ev.correct === true ? 'bg-emerald-950 text-emerald-400 border-emerald-500/80 glow-green' : (darkMode ? 'bg-transparent text-slate-500 border-[#1f2e4d] hover:border-slate-600' : 'bg-transparent text-slate-400 border-slate-300 hover:border-slate-400 hover:text-slate-600')" 
                                                                class="flex-1 py-2.5 border rounded-lg font-bold text-sm flex items-center justify-center space-x-1 transition duration-150 cursor-pointer">
                                                            <i class="fa-solid fa-check text-xs"></i>
                                                            <span>Yes</span>
                                                        </button>
                                                        <button @click="ev.correct = false" 
                                                                :class="ev.correct === false ? 'bg-rose-950 text-rose-400 border-rose-500/80' : (darkMode ? 'bg-transparent text-slate-500 border-[#1f2e4d] hover:border-slate-600' : 'bg-transparent text-slate-400 border-slate-300 hover:border-slate-400 hover:text-slate-600')" 
                                                                class="flex-1 py-2.5 border rounded-lg font-bold text-sm flex items-center justify-center space-x-1 transition duration-150 cursor-pointer">
                                                            <i class="fa-solid fa-xmark text-xs"></i>
                                                            <span>No</span>
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>

                                            <!-- Actions Bar (Save & Toggle Metadata) -->
                                            <div :class="darkMode ? 'border-[#1f2e4d]/20' : 'border-slate-200'"
                                                 class="flex items-center justify-between pt-2 border-t">
                                                <!-- Left: Toggle Metadata Link -->
                                                <button @click="showMetadata = !showMetadata" 
                                                        :class="darkMode ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-700'"
                                                        class="text-sm font-semibold flex items-center space-x-1.5 transition cursor-pointer">
                                                    <i class="fa-solid" :class="showMetadata ? 'fa-eye-slash' : 'fa-code'"></i>
                                                    <span x-text="showMetadata ? 'Hide Response Metadata & Raw Payload' : 'Show Response Metadata & Raw Payload'"></span>
                                                </button>

                                                <!-- Right: Save Pair button -->
                                                <button @click="saveReview(index, ev.correct, ev.ground_truth)" 
                                                        :disabled="savingReviewIndex === index"
                                                        :class="darkMode ? 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500' : 'bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 shadow-sm'"
                                                        class="px-5 py-2.5 rounded-xl font-bold text-sm text-white active:scale-[0.98] transition flex items-center space-x-1.5 disabled:opacity-50 cursor-pointer">
                                                    <template x-if="savingReviewIndex === index">
                                                        <i class="fa-solid fa-circle-notch fa-spin"></i>
                                                    </template>
                                                    <template x-if="savingReviewIndex !== index">
                                                        <i class="fa-solid fa-floppy-disk"></i>
                                                    </template>
                                                    <span x-text="savingReviewIndex === index ? 'Saving...' : 'Save Pair Evaluation'"></span>
                                                </button>
                                            </div>

                                            <!-- Collapsible Raw Payload & Metadata -->
                                            <div x-show="showMetadata" x-transition :class="darkMode ? 'border-[#1f2e4d]/40' : 'border-slate-200'" class="space-y-4 pt-4 border-t">
                                                <!-- Structured Metadata Grid -->
                                                <template x-if="getPairMetadata(selectedRun, index)">
                                                    <div :class="darkMode ? 'bg-[#090d16]/50 border-[#1f2e4d]/60' : 'bg-slate-50 border-slate-200'"
                                                         class="grid grid-cols-3 gap-4 p-4 rounded-xl border">
                                                        <template x-if="getPairMetadata(selectedRun, index)?.model">
                                                            <div class="space-y-1 text-left">
                                                                <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-mono">Model Name</span>
                                                                <p :class="darkMode ? 'text-blue-300' : 'text-blue-700'" class="text-sm font-mono font-semibold" x-text="getPairMetadata(selectedRun, index)?.model"></p>
                                                            </div>
                                                        </template>
                                                        <template x-if="getPairMetadata(selectedRun, index)?.tokens">
                                                            <div class="space-y-1 text-left">
                                                                <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-mono">Tokens Generated</span>
                                                                <p :class="darkMode ? 'text-purple-300' : 'text-purple-700'" class="text-sm font-mono font-semibold">
                                                                    <span class="font-bold" x-text="getPairMetadata(selectedRun, index)?.tokens?.total || 0"></span> total
                                                                    <span class="text-slate-500 text-xs" x-text="getPairMetadata(selectedRun, index)?.tokens ? '(' + getPairMetadata(selectedRun, index).tokens.prompt + ' prompt, ' + getPairMetadata(selectedRun, index).tokens.completion + ' completion)' : ''"></span>
                                                                </p>
                                                            </div>
                                                        </template>
                                                        <template x-if="getPairMetadata(selectedRun, index)?.finish_reason">
                                                            <div class="space-y-1 text-left">
                                                                <span class="text-xs font-bold text-slate-500 uppercase tracking-wider font-mono">Finish Reason</span>
                                                                <p :class="darkMode ? 'text-emerald-300' : 'text-emerald-700'" class="text-sm font-mono font-semibold flex items-center space-x-1.5">
                                                                    <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                                                    <span x-text="getPairMetadata(selectedRun, index)?.finish_reason"></span>
                                                                </p>
                                                            </div>
                                                        </template>
                                                    </div>
                                                </template>

                                                <div class="grid grid-cols-2 gap-4">
                                                    <div class="space-y-1.5 text-left">
                                                        <label class="text-xs font-bold text-slate-400 uppercase tracking-wider">Raw Input JSON</label>
                                                        <pre :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-600'"
                                                             class="h-48 overflow-y-auto custom-scrollbar border rounded-xl p-3 font-mono text-xs whitespace-pre-wrap text-left select-all" 
                                                             x-text="formatPrettyJSON(getPairInput(selectedRun, index))"></pre>
                                                    </div>
                                                    <div class="space-y-1.5 text-left">
                                                        <label class="text-xs font-bold text-slate-400 uppercase tracking-wider">Raw Output JSON</label>
                                                        <pre :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-600'"
                                                             class="h-48 overflow-y-auto custom-scrollbar border rounded-xl p-3 font-mono text-xs whitespace-pre-wrap text-left select-all" 
                                                             x-text="formatPrettyJSON(isBatchRun(selectedRun) ? selectedRun.outputs[index] : selectedRun.outputs)"></pre>
                                                    </div>
                                                </div>
                                            </div>

                                        </div>
                                    </template>
                                </div>
                            </div>
                        </template>
                    </div>

                </div>

                <!-- Ground Truth Generator View -->
                <div x-show="activeTab === 'ground_truth'" 
                     :class="darkMode ? 'glass-card border-[#1f2e4d] bg-[#131b2e]/20' : 'bg-white border-slate-200 shadow-sm'"
                     class="flex-1 flex flex-col rounded-2xl overflow-hidden border transition-all duration-300" x-transition>
                    <!-- Controls Bar -->
                    <div :class="darkMode ? 'border-[#1f2e4d] bg-[#0b0f19]/40' : 'border-slate-200 bg-slate-50/80'"
                         class="p-5 border-b flex flex-wrap items-center justify-between gap-4 transition-colors duration-300">
                        <div class="flex items-center space-x-3">
                            <div class="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg">
                                <i class="fa-solid fa-file-excel"></i>
                            </div>
                             <div>
                                <h2 :class="darkMode ? 'text-white' : 'text-slate-900'" class="text-base font-bold font-outfit">Ground Truth Labeling Playground</h2>
                                <p :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="text-sm transition-colors duration-300">Compile model inputs & outputs into clean Excel (.xlsx) templates for offline domain expert labeling.</p>
                            </div>
                        </div>

                        <div class="flex items-center space-x-4">
                            <!-- GT Search Query -->
                            <div class="relative w-64">
                                <i class="fa-solid fa-magnifying-glass absolute left-3 top-3 text-slate-400 text-sm"></i>
                                <input type="text" x-model="gtSearchQuery" placeholder="Search prompts & outputs..." 
                                       :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-white' : 'bg-white border-slate-300 text-slate-900 focus:ring-1 focus:ring-blue-500'"
                                       class="w-full border rounded-xl pl-9 pr-4 py-2 text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500 transition">
                            </div>

                            <!-- GT Correctness Filter -->
                            <div :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d]' : 'bg-slate-100 border-slate-200'"
                                 class="flex space-x-1 p-1 rounded-lg border transition-colors duration-300">
                                <button @click="gtStatusFilter = 'all'" :class="gtStatusFilter === 'all' ? (darkMode ? 'bg-[#1e293b] text-white' : 'bg-white text-slate-900 shadow-xs') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="px-3 py-1.5 text-sm rounded font-medium transition">All</button>
                                <button @click="gtStatusFilter = 'correct'" :class="gtStatusFilter === 'correct' ? (darkMode ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30' : 'bg-emerald-50 text-emerald-700 border-emerald-200') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="px-3 py-1.5 text-sm rounded font-medium transition">Correct</button>
                                <button @click="gtStatusFilter = 'incorrect'" :class="gtStatusFilter === 'incorrect' ? (darkMode ? 'bg-rose-950/80 text-rose-400 border border-rose-500/30' : 'bg-rose-50 text-rose-700 border-rose-200') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="px-3 py-1.5 text-sm rounded font-medium transition">Incorrect</button>
                                <button @click="gtStatusFilter = 'pending'" :class="gtStatusFilter === 'pending' ? (darkMode ? 'bg-[#1e293b] text-white' : 'bg-white text-slate-900 shadow-xs') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-800')" class="px-3 py-1.5 text-sm rounded font-medium transition">Pending</button>
                            </div>

                            <!-- Export Button -->
                            <button @click="downloadXLSX()" 
                                    :disabled="selectedPairKeys.length === 0"
                                    :class="selectedPairKeys.length > 0 ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold cursor-pointer font-semibold shadow-lg shadow-emerald-500/10' : 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed'"
                                    class="px-4.5 py-2.5 border border-emerald-500/20 rounded-xl text-sm flex items-center space-x-2 transition shadow-md active:scale-[0.98]">
                                <i class="fa-solid fa-download text-xs"></i>
                                <span x-text="selectedPairKeys.length > 0 ? 'Download Excel (' + selectedPairKeys.length + ')' : 'Select Pairs to Download'"></span>
                            </button>
                        </div>
                    </div>

                    <!-- Main Grid / List -->
                    <div :class="darkMode ? 'bg-[#0b0f19]/20' : 'bg-slate-50/20'"
                         class="flex-1 overflow-y-auto custom-scrollbar transition-colors duration-300">
                        <table class="w-full text-left border-collapse table-fixed">
                            <thead>
                                <tr :class="darkMode ? 'bg-[#0b0f19]/80 border-[#1f2e4d]/80 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-600'"
                                    class="border-b text-xs font-bold uppercase tracking-wider font-outfit transition-colors">
                                    <th class="py-4 px-4 w-12 text-center">
                                        <input type="checkbox" :checked="isAllPairsSelected()" @change="toggleAllPairs()"
                                               :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d]' : 'bg-white border-slate-300'"
                                               class="rounded text-blue-600 focus:ring-0 cursor-pointer w-4 h-4">
                                    </th>
                                    <th class="py-4 px-4 w-28">Status</th>
                                    <th class="py-4 px-4 w-1/3">Input Prompt</th>
                                    <th class="py-4 px-4 w-1/3">Model Output</th>
                                    <th class="py-4 px-4 w-1/4">Ground Truth Label</th>
                                </tr>
                            </thead>
                            <tbody>
                                <template x-if="filteredPairs.length === 0">
                                    <tr>
                                        <td colspan="5" class="py-12 text-center text-slate-500">
                                            <i class="fa-solid fa-inbox text-3xl mb-2 block"></i>
                                            <p class="text-sm">No matching pairs found in this dataset.</p>
                                        </td>
                                    </tr>
                                </template>
                                <template x-for="p in filteredPairs" :key="p.key">
                                    <tr :class="selectedPairKeys.includes(p.key) ? 
                                                (darkMode ? 'bg-blue-950/10 border-blue-900/40' : 'bg-blue-50/30 border-blue-200') : 
                                                (darkMode ? 'hover:bg-[#131b2e]/30 border-[#1f2e4d]/40' : 'hover:bg-slate-50/50 border-slate-200')"
                                        class="border-b transition text-sm">
                                        <td class="py-4 px-4 text-center">
                                            <input type="checkbox" :checked="selectedPairKeys.includes(p.key)" @change="togglePair(p.key)"
                                                   :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d]' : 'bg-white border-slate-300'"
                                                   class="rounded text-blue-600 focus:ring-0 cursor-pointer w-4 h-4">
                                        </td>
                                        <td class="py-4 px-4">
                                            <!-- Status Badges -->
                                            <template x-if="p.ev.correct === true">
                                                <span class="inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                                                    <i class="fa-solid fa-circle-check mr-1 text-[10px]"></i> Correct
                                                </span>
                                            </template>
                                            <template x-if="p.ev.correct === false">
                                                <span class="inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded bg-rose-950 text-rose-400 border border-rose-500/30">
                                                    <i class="fa-solid fa-circle-xmark mr-1 text-[10px]"></i> Incorrect
                                                </span>
                                            </template>
                                            <template x-if="p.ev.correct === null || p.ev.correct === undefined">
                                                <span :class="darkMode ? 'bg-[#1e293b] text-slate-400 border-[#1f2e4d]' : 'bg-slate-100 text-slate-500 border-slate-300'"
                                                      class="inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded border">
                                                    <i class="fa-solid fa-circle-question mr-1 text-[10px]"></i> Pending
                                                </span>
                                            </template>
                                        </td>
                                        <td :class="darkMode ? 'text-slate-300 hover:text-white' : 'text-slate-700 hover:text-slate-900'" class="py-4 px-4 font-mono text-sm truncate max-w-xs transition" :title="p.input" x-text="p.input"></td>
                                        <td :class="darkMode ? 'text-slate-300 hover:text-white' : 'text-slate-700 hover:text-slate-900'" class="py-4 px-4 font-outfit text-sm truncate max-w-xs transition" :title="p.output" x-text="p.output"></td>
                                        <td class="py-4 px-4">
                                            <!-- Case A: Plain Text Ground Truth -->
                                            <template x-if="!getOutputStructuredFields(p.rawOutput)">
                                                <div class="flex items-center space-x-2">
                                                    <input type="text" x-model="p.ev.ground_truth" @change="saveGTPair(p.run_id, p.item_index, p.ev.correct, p.ev.ground_truth)"
                                                           placeholder="Enter ground truth..." 
                                                           :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400 focus:ring-1 focus:ring-blue-500'"
                                                           class="w-full border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 transition font-sans">
                                                    <template x-if="p.ev.ground_truth">
                                                        <span class="text-emerald-500 text-xs flex-shrink-0" title="Ground Truth Saved">
                                                            <i class="fa-solid fa-cloud-arrow-up"></i>
                                                        </span>
                                                    </template>
                                                </div>
                                            </template>
                                            
                                            <!-- Case B: Structured Ground Truth -->
                                            <template x-if="getOutputStructuredFields(p.rawOutput)">
                                                <div class="space-y-2">
                                                    <template x-for="field in getOutputStructuredFields(p.rawOutput)" :key="field">
                                                        <div class="flex items-center space-x-2 animate-none">
                                                            <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'" class="w-20 text-xs font-mono truncate text-left" x-text="field + ':'"></span>
                                                            <input type="text" x-model="p.ev.ground_truth[field]" @change="saveGTPair(p.run_id, p.item_index, p.ev.correct, p.ev.ground_truth)"
                                                                   :placeholder="'Enter ' + field + '...'"
                                                                   :class="darkMode ? 'bg-[#090d16] border-[#1f2e4d] text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400 focus:ring-1 focus:ring-blue-500'"
                                                                   class="w-full border rounded-lg px-2.5 py-1 text-sm focus:outline-none focus:border-blue-500 transition font-sans">
                                                        </div>
                                                    </template>
                                                </div>
                                            </template>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                         </table>
                     </div>
                 </div>
             </div>
            
         </div>
     </div>

    <!-- Scripting for State Machine -->
    <script>
        document.addEventListener('alpine:init', () => {
            Alpine.data('dashboard', () => ({
                runs: [],
                loading: true,
                errorMsg: '',
                searchQuery: '',
                statusFilter: 'all',
                selectedRun: null,
                savingReviewIndex: null,
                darkMode: true,
                
                // Ground Truth Tab State
                activeTab: 'runs',
                gtSearchQuery: '',
                gtStatusFilter: 'all',
                selectedPairKeys: [],

                init() {
                    this.fetchRuns();
                },

                getOutputStructuredFields(outputObj) {
                    if (!outputObj) return null;
                    let obj = outputObj;
                    if (typeof outputObj === 'string') {
                        try {
                            obj = JSON.parse(outputObj);
                        } catch (e) {
                            return null;
                        }
                    }
                    if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
                        return null;
                    }
                    // LangChain messages check
                    if (obj.type === 'constructor' && obj.id && obj.id.includes('BaseMessage')) {
                        return null;
                    }
                    if (obj.hasOwnProperty('content') && (obj.hasOwnProperty('type') || obj.hasOwnProperty('response_metadata'))) {
                        return null;
                    }
                    // If it's a dictionary/object, return its keys
                    const keys = Object.keys(obj);
                    if (keys.length > 0) {
                        return keys;
                    }
                    return null;
                },

                async fetchRuns() {
                    this.loading = true;
                    try {
                        const res = await fetch('/api/runs');
                        if (!res.ok) throw new Error('Failed to load runs');
                        const rawRuns = await res.json();
                        
                        // Normalize evaluations on-the-fly for clean pair-wise binding
                        this.runs = rawRuns.map(run => {
                            const inputs = run.inputs;
                            const outputs = run.outputs;
                            const numItems = this.getRunBatchSize(run);
                            
                            // Dynamic Token & Cost Estimation if missing or zero (e.g. style_guide_checks)
                            if (!run.metadata) {
                                run.metadata = {};
                            }
                            if (!run.metadata.tokens || !run.metadata.tokens.total_tokens || run.metadata.tokens.total_tokens === 0) {
                                let systemPromptText = '';
                                if (run.metadata.system_prompts) {
                                    if (Array.isArray(run.metadata.system_prompts)) {
                                        systemPromptText = run.metadata.system_prompts.map(p => typeof p === 'string' ? p : JSON.stringify(p)).join('\\\\n');
                                    } else {
                                        systemPromptText = typeof run.metadata.system_prompts === 'string' ? run.metadata.system_prompts : JSON.stringify(run.metadata.system_prompts);
                                    }
                                }
                                
                                let userPromptText = '';
                                if (run.metadata.user_prompts) {
                                    if (Array.isArray(run.metadata.user_prompts)) {
                                        userPromptText = run.metadata.user_prompts.map(p => typeof p === 'string' ? p : JSON.stringify(p)).join('\\\\n');
                                    } else {
                                        userPromptText = typeof run.metadata.user_prompts === 'string' ? run.metadata.user_prompts : JSON.stringify(run.metadata.user_prompts);
                                    }
                                } else {
                                    if (Array.isArray(run.inputs)) {
                                        userPromptText = run.inputs.map(inp => typeof inp === 'string' ? inp : JSON.stringify(inp)).join('\\\\n');
                                    } else {
                                        userPromptText = typeof run.inputs === 'string' ? run.inputs : JSON.stringify(run.inputs);
                                    }
                                }
                                
                                let outputText = '';
                                if (run.outputs) {
                                    if (Array.isArray(run.outputs)) {
                                        outputText = run.outputs.map(out => typeof out === 'string' ? out : JSON.stringify(out)).join('\\\\n');
                                    } else {
                                        outputText = typeof run.outputs === 'string' ? run.outputs : JSON.stringify(run.outputs);
                                    }
                                }
                                
                                const inputChars = systemPromptText.length + userPromptText.length;
                                const outputChars = outputText.length;
                                
                                const promptTokens = Math.ceil(inputChars / 4) || 0;
                                const completionTokens = Math.ceil(outputChars / 4) || 0;
                                const totalTokens = promptTokens + completionTokens;
                                
                                // Estimated Rate: $1.50 / 1M prompt tokens, $5.00 / 1M completion tokens
                                const totalCost = (promptTokens * 0.0000015) + (completionTokens * 0.000005);
                                
                                run.metadata.tokens = {
                                    total_tokens: totalTokens,
                                    prompt_tokens: promptTokens,
                                    completion_tokens: completionTokens,
                                    total_cost: totalCost
                                };
                            }
                            
                            let evals = run.evaluation;
                            if (!Array.isArray(evals)) {
                                evals = [evals || {}];
                            }
                            
                            const normalizedEvals = [];
                            for (let i = 0; i < numItems; i++) {
                                const outp = Array.isArray(outputs) ? outputs[i] : outputs;
                                const fields = this.getOutputStructuredFields(outp);
                                
                                let gt = '';
                                if (evals[i] && evals[i].ground_truth) {
                                    gt = evals[i].ground_truth;
                                    if (fields) {
                                        if (typeof gt === 'string') {
                                            try {
                                                gt = JSON.parse(gt);
                                            } catch (e) {
                                                const obj = {};
                                                fields.forEach((f, idx) => {
                                                    obj[f] = idx === 0 ? gt : '';
                                                });
                                                gt = obj;
                                            }
                                        }
                                        // Ensure all fields are present
                                        fields.forEach(f => {
                                            if (!gt.hasOwnProperty(f)) {
                                                gt[f] = '';
                                            }
                                        });
                                    }
                                } else {
                                    if (fields) {
                                        gt = {};
                                        fields.forEach(f => {
                                            gt[f] = '';
                                        });
                                    }
                                }
                                
                                normalizedEvals.push({
                                    correct: evals[i] ? evals[i].correct : null,
                                    ground_truth: gt
                                });
                            }
                            
                            run.evaluation = normalizedEvals;
                            return run;
                        });
                        
                        // Pick first run by default if none selected or not found
                        if (this.runs.length > 0) {
                            const found = this.selectedRun ? this.runs.find(r => r.run_id === this.selectedRun.run_id) : null;
                            this.selectRun(found || this.runs[0]);
                        } else {
                            this.selectedRun = null;
                        }
                    } catch (err) {
                        this.errorMsg = err.message;
                    } finally {
                        this.loading = false;
                    }
                },

                selectRun(run) {
                    this.selectedRun = run;
                },

                async saveReview(index, correct, groundTruth) {
                    if (!this.selectedRun) return;
                    this.savingReviewIndex = index;
                    try {
                        const res = await fetch('/api/review', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            run_id: this.selectedRun.run_id,
                            item_index: index,
                            correct: correct,
                            ground_truth: groundTruth
                          })
                        });
                        if (!res.ok) throw new Error('Failed to save review');
                        
                        // Alpine.js model is already updated via reactive binding!
                    } catch (err) {
                        alert("Error saving review: " + err.message);
                    } finally {
                        this.savingReviewIndex = null;
                    }
                },

                async saveGTPair(runId, index, correct, groundTruth) {
                    try {
                        const res = await fetch('/api/review', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            run_id: runId,
                            item_index: index,
                            correct: correct,
                            ground_truth: groundTruth
                          })
                        });
                        if (!res.ok) throw new Error('Failed to save ground truth');
                    } catch (err) {
                        alert("Error saving ground truth: " + err.message);
                    }
                },

                togglePair(key) {
                    if (this.selectedPairKeys.includes(key)) {
                        this.selectedPairKeys = this.selectedPairKeys.filter(k => k !== key);
                    } else {
                        this.selectedPairKeys.push(key);
                    }
                },

                toggleAllPairs() {
                    const visibleKeys = this.filteredPairs.map(p => p.key);
                    const allSelected = visibleKeys.every(k => this.selectedPairKeys.includes(k));
                    if (allSelected) {
                        this.selectedPairKeys = this.selectedPairKeys.filter(k => !visibleKeys.includes(k));
                    } else {
                        visibleKeys.forEach(k => {
                            if (!this.selectedPairKeys.includes(k)) {
                                this.selectedPairKeys.push(k);
                            }
                        });
                    }
                },

                isAllPairsSelected() {
                    const visibleKeys = this.filteredPairs.map(p => p.key);
                    if (visibleKeys.length === 0) return false;
                    return visibleKeys.every(k => this.selectedPairKeys.includes(k));
                },

                downloadXLSX() {
                    const selectedPairs = this.allPairs.filter(p => this.selectedPairKeys.includes(p.key));
                    if (selectedPairs.length === 0) {
                        alert("Please select at least one pair to download.");
                        return;
                    }
                    
                    const firstPair = selectedPairs[0];
                    const fields = this.getOutputStructuredFields(firstPair.rawOutput);
                    
                    let excelData = [];
                    let colWidths = [];
                    
                    if (fields) {
                        excelData = selectedPairs.map(p => {
                            const row = {
                                "Input": p.input
                            };
                            
                            // Get parsed model output object
                            let modelOutObj = p.rawOutput;
                            if (typeof modelOutObj === 'string') {
                                try {
                                    modelOutObj = JSON.parse(modelOutObj);
                                } catch (e) {
                                    modelOutObj = {};
                                }
                            }
                            
                            // Populate model output columns
                            fields.forEach(f => {
                                row[`Model Output - ${f}`] = (modelOutObj && modelOutObj.hasOwnProperty(f)) ? modelOutObj[f] : '';
                            });
                            
                            // Populate ground truth columns
                            fields.forEach(f => {
                                let gtVal = '';
                                if (p.ev.correct === true) {
                                    gtVal = (p.ev.ground_truth && p.ev.ground_truth.hasOwnProperty(f) && p.ev.ground_truth[f] !== '') 
                                            ? p.ev.ground_truth[f] 
                                            : ((modelOutObj && modelOutObj.hasOwnProperty(f)) ? modelOutObj[f] : '');
                                } else {
                                    gtVal = (p.ev.ground_truth && p.ev.ground_truth.hasOwnProperty(f)) ? p.ev.ground_truth[f] : '';
                                }
                                row[`Ground Truth - ${f}`] = gtVal;
                            });
                            
                            return row;
                        });
                        
                        colWidths.push({ wch: 60 });
                        fields.forEach(() => colWidths.push({ wch: 30 }));
                        fields.forEach(() => colWidths.push({ wch: 30 }));
                    } else {
                        excelData = selectedPairs.map(p => {
                            let gtVal = '';
                            if (p.ev.correct === true) {
                                gtVal = p.ev.ground_truth || p.output;
                            } else {
                                gtVal = p.ev.ground_truth || '';
                            }
                            return {
                                "Input": p.input,
                                "Model Output": p.output,
                                "Ground Truth": gtVal
                            };
                        });
                        
                        colWidths = [
                            { wch: 60 },
                            { wch: 60 },
                            { wch: 60 }
                        ];
                    }
                    
                    const ws = XLSX.utils.json_to_sheet(excelData);
                    ws['!cols'] = colWidths;
                    
                    const wb = XLSX.utils.book_new();
                    XLSX.utils.book_append_sheet(wb, ws, "Ground Truth Template");
                    
                    const datasetName = "{{DATASET_NAME}}";
                    XLSX.writeFile(wb, `${datasetName}_ground_truth_template.xlsx`);
                },

                 get allPairs() {
                     const pairs = [];
                     this.runs.forEach(run => {
                         const numItems = this.getRunBatchSize(run);
                         const evals = Array.isArray(run.evaluation) ? run.evaluation : [run.evaluation || {}];
                         
                         for (let i = 0; i < numItems; i++) {
                             const inp = this.getPairInput(run, i);
                             const outp = Array.isArray(run.outputs) ? run.outputs[i] : run.outputs;
                             const ev = evals[i] || { correct: null, ground_truth: '' };
                             
                             pairs.push({
                                 run_id: run.run_id,
                                 item_index: i,
                                 timestamp: run.timestamp,
                                 input: this.getCleanText(inp),
                                 output: this.getCleanText(outp),
                                 rawOutput: outp,
                                 ev: ev,
                                 key: `${run.run_id}_${i}`
                             });
                         }
                     });
                     return pairs;
                 },
 
                 get filteredPairs() {
                     const query = this.gtSearchQuery.toLowerCase();
                     return this.allPairs.filter(p => {
                         let gtSearchStr = '';
                         if (p.ev.ground_truth) {
                             if (typeof p.ev.ground_truth === 'object') {
                                 gtSearchStr = Object.values(p.ev.ground_truth).join(' ');
                             } else {
                                 gtSearchStr = String(p.ev.ground_truth);
                             }
                         }
                         const matchSearch = p.input.toLowerCase().includes(query) || 
                                              p.output.toLowerCase().includes(query) || 
                                              gtSearchStr.toLowerCase().includes(query);
                         let matchStatus = true;
                         if (this.gtStatusFilter === 'correct') {
                             matchStatus = p.ev.correct === true;
                         } else if (this.gtStatusFilter === 'incorrect') {
                             matchStatus = p.ev.correct === false;
                         } else if (this.gtStatusFilter === 'pending') {
                             matchStatus = p.ev.correct === null || p.ev.correct === undefined;
                         }
                         return matchSearch && matchStatus;
                     });
                 },
 
                 getSystemPromptsText() {
                     if (!this.selectedRun || !this.selectedRun.metadata) return '';
                     const prompts = this.selectedRun.metadata.system_prompts;
                     if (!prompts) return '';
                     if (Array.isArray(prompts)) {
                         return prompts.map(p => typeof p === 'string' ? p : JSON.stringify(p)).join('\\\\n\\\\n');
                     }
                     if (typeof prompts === 'string') {
                         return prompts;
                     }
                     return JSON.stringify(prompts);
                 },
 
                 getRunBatchSize(run) {
                     if (!run) return 0;
                     if (Array.isArray(run.outputs)) return run.outputs.length;
                     if (Array.isArray(run.inputs)) return run.inputs.length;
                     return 1;
                 },
 
                  getPairInput(run, index) {
                      if (!run) return '';
                      const batchSize = this.getRunBatchSize(run);
                      if (run.metadata && Array.isArray(run.metadata.user_prompts)) {
                          const prompts = run.metadata.user_prompts;
                          if (prompts.length === batchSize) {
                              return prompts[index];
                          }
                          // Try consecutive deduplication after stripping whitespace
                          const deduped = [];
                          for (let i = 0; i < prompts.length; i++) {
                              const p = prompts[i];
                              if (typeof p === 'string') {
                                  const pStripped = p.trim();
                                  if (deduped.length === 0 || deduped[deduped.length - 1].trim() !== pStripped) {
                                      deduped.push(p);
                                  }
                              } else {
                                  deduped.push(p);
                              }
                          }
                          if (deduped.length === batchSize) {
                              return deduped[index];
                          }
                      }
                      if (Array.isArray(run.inputs) && run.inputs.length === batchSize) {
                          return run.inputs[index];
                      }
                      if (run.inputs && typeof run.inputs === 'object') {
                          if (run.inputs.chain && typeof run.inputs.chain === 'object') {
                              const arrayKey = Object.keys(run.inputs).find(k => k !== 'chain' && Array.isArray(run.inputs[k]) && run.inputs[k].length === batchSize);
                              if (arrayKey) {
                                  return run.inputs[arrayKey][index];
                              }
                          } else {
                              const arrayKey = Object.keys(run.inputs).find(k => Array.isArray(run.inputs[k]) && run.inputs[k].length === batchSize);
                              if (arrayKey) {
                                  return run.inputs[arrayKey][index];
                              }
                          }
                      }
                      return run.inputs;
                  },
 
                 // Helper to summarize inputs cleanly for the sidebar list
                 getSidebarPreview(run) {
                     if (!run) return '';
                     const batchSize = this.getRunBatchSize(run);
                     if (batchSize > 1) {
                         const previews = [];
                         for (let i = 0; i < Math.min(batchSize, 3); i++) {
                             const inp = this.getPairInput(run, i);
                             previews.push(this.getCleanText(inp));
                         }
                         let previewText = `Batch (${batchSize}): ` + previews.join(' | ');
                         if (batchSize > 3) {
                             previewText += ' ...';
                         }
                         return previewText;
                     } else {
                         const inp = this.getPairInput(run, 0);
                         return this.getCleanText(inp);
                     }
                 },

                // Helper to extract granular pair-wise metadata (Model Name, Tokens, Finish Reason)
                getPairMetadata(run, index) {
                    if (!run) return null;
                    const output = this.isBatchRun(run) ? run.outputs[index] : run.outputs;
                    if (!output || typeof output !== 'object') return null;

                    const metadata = {};
                    
                    // Model
                    if (output.response_metadata && output.response_metadata.model_name) {
                        metadata.model = output.response_metadata.model_name;
                    } else if (output.response_metadata && output.response_metadata.model) {
                        metadata.model = output.response_metadata.model;
                    }
                    
                    // Provider
                    if (output.response_metadata && output.response_metadata.model_provider) {
                        metadata.provider = output.response_metadata.model_provider;
                    }

                    // Finish Reason
                    if (output.response_metadata && output.response_metadata.finish_reason) {
                        metadata.finish_reason = output.response_metadata.finish_reason;
                    }

                    // Token usage
                    let tokens = null;
                    if (output.usage_metadata) {
                        tokens = {
                            total: output.usage_metadata.total_tokens,
                            prompt: output.usage_metadata.input_tokens,
                            completion: output.usage_metadata.output_tokens
                        };
                    } else if (output.response_metadata && output.response_metadata.token_usage) {
                        const tu = output.response_metadata.token_usage;
                        tokens = {
                            total: tu.total_tokens,
                            prompt: tu.prompt_tokens,
                            completion: tu.completion_tokens
                        };
                    }
                    if (tokens) {
                        metadata.tokens = tokens;
                    }

                    if (Object.keys(metadata).length === 0) return null;
                    return metadata;
                },

                // Helper to check if a run is a batch execution
                isBatchRun(run) {
                    if (!run) return false;
                    return Array.isArray(run.outputs);
                },

                // Stringifiers & Formatting
                getCleanText(val) {
                    if (!val) return '';
                    if (typeof val === 'string') {
                        try {
                            const parsed = JSON.parse(val);
                            return this.getCleanText(parsed);
                        } catch (e) {
                            return val;
                        }
                    }
                    if (typeof val === 'object') {
                        // Check if it is a LangChain message or message list
                        if (Array.isArray(val)) {
                            return val.map(v => this.getCleanText(v)).join('\\n');
                        }
                        // LangChain constructor format
                        if (val.type === 'constructor' && val.kwargs && val.kwargs.content !== undefined) {
                            return this.getCleanText(val.kwargs.content);
                        }
                        // LangChain standard message format
                        if (val.content !== undefined) {
                            return this.getCleanText(val.content);
                        }
                        if (val.kwargs && val.kwargs.content !== undefined) {
                            return this.getCleanText(val.kwargs.content);
                        }
                        // Simple dictionary (e.g. prompt variables)
                        const keys = Object.keys(val);
                        if (keys.length > 0) {
                            const isSimple = keys.every(k => typeof val[k] !== 'object');
                            if (isSimple) {
                                return keys.map(k => `${k}: ${val[k]}`).join('\\n');
                            }
                        }
                        return JSON.stringify(val, null, 2);
                    }
                    return String(val);
                },

                stringifyPayload(val) {
                    if (typeof val === 'string') return val;
                    if (typeof val === 'object') {
                        if (Array.isArray(val) && val.length > 0) {
                            const item = val[0];
                            if (typeof item === 'object') {
                                return JSON.stringify(val);
                            }
                        }
                        return JSON.stringify(val);
                    }
                    return String(val);
                },

                formatPrettyJSON(val) {
                    if (typeof val === 'string') {
                        try {
                            const parsed = JSON.parse(val);
                            return JSON.stringify(parsed, null, 2);
                        } catch (e) {
                            return val;
                        }
                    }
                    return JSON.stringify(val, null, 2);
                },

                formatTime(timestamp) {
                    try {
                        const date = new Date(timestamp);
                        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    } catch (e) {
                        return '';
                    }
                },

                // Metric Getters
                get totalRuns() { return this.runs.length; },

                get avgDuration() {
                    if (!this.runs.length) return 0;
                    const sum = this.runs.reduce((acc, r) => acc + (r.metadata?.duration_seconds || 0), 0);
                    return (sum / this.runs.length).toFixed(2);
                },

                get totalCost() {
                    const sum = this.runs.reduce((acc, r) => acc + (r.metadata?.tokens?.total_cost || 0), 0);
                    return sum.toFixed(4);
                },

                get accuracy() {
                    let totalReviewedPairs = 0;
                    let correctPairs = 0;
                    
                    this.runs.forEach(run => {
                        if (Array.isArray(run.evaluation)) {
                            run.evaluation.forEach(ev => {
                                if (ev.correct !== null && ev.correct !== undefined) {
                                    totalReviewedPairs++;
                                    if (ev.correct === true) {
                                        correctPairs++;
                                    }
                                }
                            });
                        }
                    });
                    
                    if (totalReviewedPairs === 0) return 'N/A';
                    return ((correctPairs / totalReviewedPairs) * 100).toFixed(0) + '%';
                },

                // Get run status badge components
                getRunStatus(run) {
                    if (!run || !Array.isArray(run.evaluation)) return { type: 'pending', label: 'Pending' };
                    const total = run.evaluation.length;
                    const correct = run.evaluation.filter(ev => ev.correct === true).length;
                    const incorrect = run.evaluation.filter(ev => ev.correct === false).length;
                    
                    if (incorrect > 0) return { type: 'incorrect', label: `${incorrect}/${total} Incorrect` };
                    if (correct === total) return { type: 'correct', label: 'Correct' };
                    if (correct > 0) return { type: 'partial', label: `${correct}/${total} Correct` };
                    return { type: 'pending', label: 'Pending' };
                },

                // Filter logic
                get filteredRuns() {
                    return this.runs.filter(run => {
                        const inputStr = typeof run.inputs === 'object' ? JSON.stringify(run.inputs) : String(run.inputs);
                        const outputStr = typeof run.outputs === 'object' ? JSON.stringify(run.outputs) : String(run.outputs);
                        const matchSearch = inputStr.toLowerCase().includes(this.searchQuery.toLowerCase()) || 
                                             outputStr.toLowerCase().includes(this.searchQuery.toLowerCase());
                        
                        let matchStatus = true;
                        const status = this.getRunStatus(run).type;
                        if (this.statusFilter === 'correct') {
                            matchStatus = status === 'correct';
                        } else if (this.statusFilter === 'incorrect') {
                            matchStatus = status === 'incorrect';
                        } else if (this.statusFilter === 'pending') {
                            matchStatus = status === 'pending' || status === 'partial';
                        }
                        
                        return matchSearch && matchStatus;
                    });
                }
            }));
        });
    </script>
</body>
</html>
"""


class VisualizerHTTPHandler(BaseHTTPRequestHandler):
    """Custom HTTP server handler to serve the SPA and API endpoints."""

    def log_message(self, format, *args):
        # Silence console log messages for a clean command-line experience
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            rendered = HTML_TEMPLATE.replace("{{DATASET_NAME}}", self.server.dataset_name)
            self.wfile.write(rendered.encode("utf-8"))
        elif self.path == "/api/runs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            runs = []
            file_path = self.server.dataset_file
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    runs.append(json.loads(line))
                                except Exception:
                                    pass
                except Exception:
                    pass
            
            # Sort runs by timestamp descending (most recent first)
            runs.reverse()
            self.wfile.write(json.dumps(runs, cls=RobustEncoder).encode("utf-8"))
        elif self.path == "/api/download":
            file_path = self.server.dataset_file
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-type", "application/x-jsonlines; charset=utf-8")
                self.send_header("Content-Disposition", f"attachment; filename={self.server.dataset_name}.jsonl")
                self.end_headers()
                try:
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                except Exception as e:
                    self.wfile.write(str(e).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/review":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                run_id = data.get("run_id")
                item_index = data.get("item_index", 0)
                correct = data.get("correct")
                ground_truth = data.get("ground_truth")

                from eval_factory.storage import update_run
                success = update_run(
                    dataset_name=self.server.dataset_name,
                    run_id=run_id,
                    item_index=item_index,
                    evaluation_update={"correct": correct, "ground_truth": ground_truth},
                    base_dir=self.server.base_dir
                )

                if success:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))


def find_free_port() -> int:
    """Finds an open ephemeral port on the host machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_visualizer(dataset_name: str, port: int = 0, host: str = "127.0.0.1", base_dir: str = None):
    """
    Spins up the zero-dependency local dashboard server and opens the default browser.

    Args:
        dataset_name: Name of the dataset file (without .jsonl).
        port: Specific port to bind to. If 0, searches for an open port.
        host: Host interface to bind to (default: '127.0.0.1'). Use '0.0.0.0' for LAN access.
        base_dir: Optional directory override where datasets live.
    """
    target_dir = base_dir or config.base_dir
    safe_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in dataset_name])
    dataset_file = os.path.abspath(os.path.join(target_dir, f"{safe_name}.jsonl"))

    if not port:
        port = find_free_port()

    server_address = (host, port)
    httpd = HTTPServer(server_address, VisualizerHTTPHandler)
    
    # Store parameters in server context for request handler access
    httpd.dataset_name = dataset_name
    httpd.dataset_file = dataset_file
    httpd.base_dir = target_dir

    display_host = "localhost" if host == "127.0.0.1" else host
    url = f"http://{display_host}:{port}/"
    print("=" * 60)
    print(f"🚀 eval-factory visualization server starting!")
    print(f"   Dataset:  {dataset_name} ({dataset_file})")
    print(f"   Address:  {url}")
    print("=" * 60)
    print("Press Ctrl+C to terminate the visualizer...")

    # Automatically open standard browser after a tiny sleep in thread (only for local loopback)
    if host == "127.0.0.1":
        def open_browser():
            webbrowser.open(url)
        threading.Timer(0.8, open_browser).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping visualizer server...")
        httpd.server_close()
        sys.exit(0)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Start the eval-factory visualization dashboard.")
    parser.add_argument("dataset", help="Name or path of the dataset .jsonl file")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to (default: 127.0.0.1). Use 0.0.0.0 for LAN access.")
    parser.add_argument("--port", type=int, default=0, help="Port to bind to (default: random open port)")
    
    args = parser.parse_args()
    
    dataset_path = args.dataset
    
    # Handle files passed with extension
    if dataset_path.endswith(".jsonl"):
        dataset_path = dataset_path[:-6]
    
    # Extract base directory and actual dataset name
    base_dir = os.path.dirname(dataset_path)
    dataset_name = os.path.basename(dataset_path)
    
    # If base_dir is empty, default to None to fall back to config.base_dir
    if not base_dir:
        base_dir = None
    
    # Run server
    start_visualizer(dataset_name, port=args.port, host=args.host, base_dir=base_dir)


if __name__ == "__main__":
    main()

