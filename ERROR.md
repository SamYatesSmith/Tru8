Unhandled Runtime Error
TypeError: Cannot read properties of undefined (reading 'credibility_score')

Source
app\dashboard\check\[id]\components\overall-summary-card.tsx (21:49) @ credibility_score

  19 |   };
  20 |
> 21 |   const credibility = getCredibilityLevel(check.credibility_score);
     |                                                 ^
  22 |
  23 |   return (
  24 |     <div className="bg-gradient-to-br from-blue-950/50 to-purple-950/50 border-2 border-blue-500/30 rounded-xl p-8 mb-8">