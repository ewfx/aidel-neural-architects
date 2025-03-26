import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import wflogo from "../assets/icons/wflogo1.png";


function HomePage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];

    if (!file) {
      alert("Please select a file");
      return;
    }

    if (!file.name.endsWith(".csv") && !file.name.endsWith(".txt")) {
      alert("Please select a valid CSV or TXT file");
      return;
    }

    try {
      setIsLoading(true);

      const filename = file.name;

      const formData = new FormData();
      formData.append("dataFile", file);

      const response = await fetch("http://127.0.0.1:5000/upload", {
        method: "POST",
        body: formData,
      });

      if (response.status === 200) {
        const result = await response.text();
        setIsLoading(false);

        navigate("/result", { state: { result, filename } });
      } else {
        setIsLoading(false);
        alert("File upload failed");
      }
    } catch (error) {
      setIsLoading(false);
      console.error("Error uploading file:", error);
      alert("File upload failed");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
  <div className="bg-[#b31e30] p-4 flex justify-between items-center">
    <h1 className="text-yellow-400 text-3xl font-clarendon">
      WELLS FARGO
    </h1>
    <img src={wflogo} alt="logo" className="h-14 w-auto" />
  </div>


      <h1 className="text-5xl flex justify-center font-clarendon font-bold pt-12">
        AI Driven Entity Intelligence Risk Analysis
      </h1>
      {/* <br />
      <h2 className="text-2xl flex justify-center font-serif">
        in .txt/.csv format
      </h2> */}
      <div className="flex-grow flex items-center justify-center">
        {isLoading ? (
          <div className="flex items-center mb-52">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            <span className="ml-4 text-xl">Uploading...</span>
          </div>
        ) : (
          <label className="bg-[#b31e30] hover:bg-opacity-90 text-yellow-400 font-clarendon font-bold py-4 px-6 rounded-full text-2xl shadow-lg cursor-pointer mb-52">
            Upload File
            <input
              type="file"
              id="upload-button"
              onChange={handleFileUpload}
              className="hidden"
              accept=".csv,.txt"
            />
          </label>
        )}        
      </div>
      <footer className="flex justify-between bg-[#b31e30] text-white text-sm py-2 px-7 max-sm:text-xs">
        <div>&copy; {new Date().getFullYear()} Wells Fargo</div>
        <div>
          Developed by Neural_Architects
        </div>
      </footer>
    </div>
  );
}

export default HomePage;
