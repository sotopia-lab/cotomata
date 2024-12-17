"use client"

// import React, { useState } from 'react';
// import { Card, CardContent } from './ui/card';
// import { ScrollArea } from "@/components/ui/scroll-area";

// // Define the props for the Browser component
// interface BrowserProps {
//   url: string; // The initial URL to load
// }

// // Main Browser component definition
// export const Browser: React.FC<BrowserProps> = ({ url }) => {
//     const [currentUrl, setCurrentUrl] = useState(url); // State to manage the current URL

//     // const proxyUrl = `https://cors-anywhere.herokuapp.com/${currentUrl}`;

//     return (
//       <div className="h-[67vh] bg-[#1e1e1e] border-b border-gray-700 flex flex-col">
//         <div className="flex items-center p-2 bg-[#252526] border-b border-gray-700">
//           <input
//             value={currentUrl} // Bind input value to currentUrl state
//             onChange={(e) => setCurrentUrl(e.target.value)} // Update currentUrl on input change
//             placeholder="Enter URL" // Placeholder text for the input field
//           />
//           <button onClick={() => setCurrentUrl(currentUrl)}>Go</button> {/* Button to navigate to the current URL */}
//         </div>
//         <div className="flex-1 bg-white">
//           <iframe src={currentUrl} className="w-full h-full border-none" /> {/* Display the web content in an iframe */}
//         </div>
//       </div>
//     );
// };
import { useState } from 'react';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus, X } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";

interface BrowserProps {
  url: string; // The initial URL to load
}

export const Browser: React.FC<BrowserProps> = ({ url }) => {
  const [currentUrl, setCurrentUrl] = useState(url); // State to manage the current URL
  const [openTabs, setOpenTabs] = useState([
    { path: currentUrl },
  ]);
  const [activeTab, setActiveTab] = useState(0);

  const handleTabSelect = (index: number) => setActiveTab(index);
  const handleTabClose = (index: number) => {
    const newTabs = [...openTabs];
    newTabs.splice(index, 1);
    setOpenTabs(newTabs);
    if (activeTab === index && newTabs.length > 0) {
      setActiveTab(0);
    }
  };

  const handleUrlSubmit = () => {
    if (currentUrl) {
      setOpenTabs([...openTabs, { path: currentUrl }]);
      setActiveTab(openTabs.length);
    }
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentUrl(e.target.value);
    if (openTabs[activeTab]) {
      const updatedTabs = [...openTabs];
      updatedTabs[activeTab].path = e.target.value; // Update the URL of the active tab
      setOpenTabs(updatedTabs);
    }
  };

  return (
    <Card className="flex h-full w-full flex-col">
      <CardHeader className="border-b p-0">
        <div className="flex items-center gap-2 p-2">
          <input
            type="text"
            value={url}
            onChange={handleUrlChange}
            placeholder="Enter URL"
            className="p-2 flex-1 rounded-md border"
          />
          <Button onClick={handleUrlSubmit} variant="ghost">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <ScrollArea className="w-full">
          <div className="flex min-w-max gap-1">
            {openTabs.map((tab, index) => (
              <Button
                key={tab.path}
                variant={index === activeTab ? "secondary" : "ghost"}
                className="group relative h-9 rounded-none px-4"
                onClick={() => handleTabSelect(index)}
              >
                <span className="max-w-[150px] truncate">{tab.path}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-1/2 h-6 w-6 -translate-y-1/2 opacity-0 group-hover:opacity-100"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTabClose(index);
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </Button>
            ))}
          </div>
        </ScrollArea>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        {openTabs[activeTab] && (
          <iframe
            src={openTabs[activeTab].path}
            className="w-full h-full border-none"
          />
        )}
      </CardContent>
    </Card>
  );
};
