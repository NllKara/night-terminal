import React from'react';
import{createRoot}from'react-dom/client';
import ProductionApp from'./ProductionApp';
import TerminalEnhancements from'./TerminalEnhancements';
import FastKeySave from'./FastKeySave';
import NightChartInjector from'./NightChartInjector';
import'./style.css';
import'./institution.css';
import'./equity.css';
import'./production.css';
import'./ndr-layout.css';
import'./news-prediction.css';
import'./orderflow.css';
import'./tablet-fixes.css';
import'./macro-prediction.css';
import'./night-chart.css';

createRoot(document.getElementById('root')).render(<><ProductionApp/><TerminalEnhancements/><FastKeySave/><NightChartInjector/></>);
