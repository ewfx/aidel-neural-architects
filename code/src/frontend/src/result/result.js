import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { DataGrid } from "@mui/x-data-grid";
import homesvg from "../assets/icons/home.svg";

const columns_local = [
  { field: "id", headerName: "ID", type: "string", width: 100 },
  { field: "transaction_id", headerName: "Txn ID", type: "string", width: 150 },
  { field: "extracted_entities", headerName: "Entity Names", type: "string", width: 300 },
  { field: "entity_type", headerName: "Entity Type", type: "string", width: 250 },
  { field: "risk_score", headerName: "Risk Score", type: "number", width: 150 },
  { field: "supporting_evidence", headerName: "Supporting Evidence", type: "string", width: 300 },
  { field: "confidence_score", headerName: "Confidence Score", type: "number", width: 200 },
  { field: "reason", headerName: "Reason", type: "string", width: 600 },
];

function ResultPage() {
  const location = useLocation();
  const result = location.state?.result;
  const filename = location.state?.filename.split(".")[0]; 
  
  const navigate = useNavigate();

  if(!result) {
    window.location.href = window.location.href.replace('/result', '/');
  }

  const parsedResult = JSON.parse(result);

  let columns = columns_local;
  let rows = parsedResult.map((row, index) => ({
    id: index + 1,
    transaction_id: row.transaction_id,
    extracted_entities: row.extracted_entities.join(", "),
    entity_type: row.entity_type.join(", "),
    risk_score: row.risk_score,
    supporting_evidence: row.supporting_evidence.join(", "),
    confidence_score: row.confidence_score,
    reason: row.reason,
    remark: row.remark,
  }));  

  const handleDownloadClickJSON = () => {
    try {
      if (!rows || rows.length === 0) {
        console.error("No valid transactions found in JSON data.");
        return;
      }
      const downloadFileName1 = `risks_${filename}_json`;
      const jsonContent = JSON.stringify(rows, null, 2);
  
      const blob1 = new Blob([jsonContent], { type: "application/json" });
      const url1 = URL.createObjectURL(blob1);
      
      const link1 = document.createElement("a");
      link1.href = url1;
      link1.download = downloadFileName1;
      
      document.body.appendChild(link1);
      link1.click();
      document.body.removeChild(link1);  
    } catch (error) {
      console.error("Error generating JSON:", error);
    }
  };

  const handleDownloadClickCSV = () => {
    try {
      if (!rows || rows.length === 0) {
        console.error("No valid transactions found in JSON data.");
        return;
      }
  
      const downloadFileName = `risks_${filename}_csv`;
      const headers = [
        "transaction_id", "company1", "company2",
        "entity_type_1", "entity_type_2", "risk_score",
        "supporting_evidence", "confidence_score", "reason"
      ];
  
      const csvData = rows.map(transaction => [
        transaction.transaction_id,
        transaction.extracted_entities?.split(',')[0] || "",
        transaction.extracted_entities?.split(',')[1] || "",
        transaction.entity_type?.split(',')[0] || "",
        transaction.entity_type?.split(',')[1] || "",
        transaction.risk_score,
        `"${Array.isArray(transaction.supporting_evidence) ? transaction.supporting_evidence.join("; ").replace(/"/g, '""') : transaction.supporting_evidence || ""}"`,
        transaction.confidence_score,
        `"${transaction.reason.replace(/"/g, '""')}"`
      ]);
  
    const csvContent = [headers.join(","), ...csvData.map(row => row.join(","))].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = downloadFileName;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    } catch (error) {
      console.error("Error generating CSV:", error);
    }
  };  

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-[#b31e30] flex justify-between items-center py-3 px-7">
        <h1 className="text-yellow-400 text-3xl font-clarendon">
          Tweet Classifier
        </h1>
        <div
          className="flex items-center hover:opacity-70 cursor-pointer"
          onClick={() => navigate("/")}
        >
          <img src={homesvg} alt="home" className="mr-1" />
          <h1 className="text-yellow-400 text-2xl font-clarendon">Home</h1>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center -mt-11 h-screen">
        <div className="px-32 flex flex-row justify-between items-center w-full mb-6">
          <h1 className="text-4xl font-sans font-bold">Results</h1>
          <div className="flex gap-x-4">
          <label
            className="bg-[#b31e30] hover:bg-opacity-90 text-yellow-400 font-bold py-2 px-3 rounded-full text-xl shadow-lg cursor-pointer"
            onClick={handleDownloadClickJSON}
          >
            Download JSON File
          </label>
          <label
            className="bg-[#b31e30] hover:bg-opacity-90 text-yellow-400 font-bold py-2 px-3 rounded-full text-xl shadow-lg cursor-pointer"
            onClick={handleDownloadClickCSV}
          >
            Download CSV File
          </label>
          </div>
        </div>
        <div className="w-11/12 h-2/3">
          <DataGrid
            rows={rows}
            columns={columns}
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 10 },
              },
            }}
            pageSizeOptions={[10, 20, 50, 100]}
          />
        </div>
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

export default ResultPage;
